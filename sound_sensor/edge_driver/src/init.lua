local Driver = require "st.driver"
local capabilities = require "st.capabilities"
local log = require "log"

local pi_http = require "pi_http"

local DRIVER_NAME = "pi-sound-sensor"

local function get_pref(device, key, default)
  if device.preferences and device.preferences[key] ~= nil then
    return device.preferences[key]
  end
  return default
end

-- ---------- emit helpers (only when changed) ----------

local function emit_switch_if_changed(device, is_on)
  local last = device:get_field("last_switch")
  if last ~= nil and last == is_on then return end
  device:set_field("last_switch", is_on, { persist = false })

  if is_on then
    device:emit_event(capabilities.switch.switch.on())
  else
    device:emit_event(capabilities.switch.switch.off())
  end
end

local function emit_sound_sensor_if_changed(device, detected)
  local last = device:get_field("last_sound_detected")
  if last ~= nil and last == detected then return end
  device:set_field("last_sound_detected", detected, { persist = false })

  local cap = capabilities.soundSensor
  if not cap or not cap.sound then return end

  -- Try named constructors if available, else fall back to enum string
  local ok, evt = pcall(function()
    if detected and cap.sound.detected then
      return cap.sound.detected()
    end
    if (not detected) and cap.sound.notDetected then
      return cap.sound.notDetected()
    end
    return cap.sound(detected and "detected" or "not detected")
  end)

  if ok and evt then
    device:emit_event(evt)
  else
    device:emit_event(cap.sound(detected and "detected" or "not detected"))
  end
end

local function clamp_int(x, lo, hi)
  if x < lo then return lo end
  if x > hi then return hi end
  return x
end

local function map_db_to_spl(db, offset)
  -- db is typically negative (dBFS). We map to a 0..194 UI value.
  -- spl = clamp(round(db + offset), 0, 194)
  local v = math.floor((db + offset) + 0.5)
  return clamp_int(v, 0, 194)
end

local function emit_spl_if_changed(device, spl_value)
  local last = device:get_field("last_spl")
  if last ~= nil and last == spl_value then return end
  device:set_field("last_spl", spl_value, { persist = false })

  local spl_cap = capabilities["soundPressureLevel"] or capabilities.soundPressureLevel
  if not spl_cap or not spl_cap.soundPressureLevel then return end

  -- Prefer {value, unit} then fallback to plain number
  local evt_ok, evt = pcall(function()
    return spl_cap.soundPressureLevel({ value = spl_value, unit = "dB" })
  end)
  if evt_ok and evt then
    device:emit_event(evt)
    return
  end

  local ok2, evt2 = pcall(function()
    return spl_cap.soundPressureLevel(spl_value)
  end)
  if ok2 and evt2 then
    device:emit_event(evt2)
  end
end

-- ---------- parsing helpers ----------

local function normalize_trigger(v)
  if v == true then return true end
  if v == false then return false end
  if type(v) == "number" then return v ~= 0 end
  if type(v) == "string" then
    local s = v:lower()
    if s == "1" or s == "true" or s == "on" or s == "detected" then return true end
    if s == "0" or s == "false" or s == "off" or s == "not_detected" or s == "not detected" then return false end
  end
  return false
end

local function extract_db_and_trigger(data)
  if type(data) ~= "table" then return nil, nil end
  local db = data.db or data.spl or data.soundPressureLevel
  local trig = data.trigger
  if trig == nil then trig = data.detected end
  if trig == nil then trig = data.on end
  return tonumber(db), trig
end

-- ---------- polling ----------

local function poll_once(driver, device)
  local host = get_pref(device, "piHost", "192.168.68.63")
  local port = tonumber(get_pref(device, "piPort", 8787)) or 8787
  local path = get_pref(device, "httpPath", "/state")
  local timeout_s = tonumber(get_pref(device, "httpTimeout", 2)) or 2
  local offset = tonumber(get_pref(device, "dbOffset", 120)) or 120

  local data, err = pi_http.get_json(host, port, path, timeout_s)
  if not data then
    log.warn(string.format("poll failed: %s (host=%s port=%d path=%s)", tostring(err), tostring(host), port, tostring(path)))
    return
  end

  local db, trig_raw = extract_db_and_trigger(data)
  local detected = normalize_trigger(trig_raw)

  -- 1) switch => Loud Event semantics (only changes emit)
  emit_switch_if_changed(device, detected)

  -- 2) Sound Sensor line (detected / not detected)
  emit_sound_sensor_if_changed(device, detected)

  -- 3) SPL line: mapped 0..194
  if db ~= nil then
    local spl = map_db_to_spl(db, offset)
    emit_spl_if_changed(device, spl)
  end
end

local function cancel_poll_timer(device)
  local timer = device:get_field("poll_timer")
  if timer then
    device.thread:cancel_timer(timer)
    device:set_field("poll_timer", nil, { persist = false })
  end
end

local function ensure_poll_timer(driver, device)
  cancel_poll_timer(device)

  local interval = tonumber(get_pref(device, "pollSeconds", 1)) or 1
  if interval < 1 then interval = 1 end

  local timer = device.thread:call_on_schedule(interval, function()
    poll_once(driver, device)
  end, "pi_poll")

  device:set_field("poll_timer", timer, { persist = false })
end

-- ---------- lifecycle ----------

local function device_added(driver, device)
  -- Initialize UI state once (won't spam after because we gate by last_* fields)
  emit_switch_if_changed(device, false)
  emit_sound_sensor_if_changed(device, false)
  emit_spl_if_changed(device, 0)

  ensure_poll_timer(driver, device)
  poll_once(driver, device)
end

local function device_init(driver, device)
  ensure_poll_timer(driver, device)
end

local function device_removed(driver, device)
  cancel_poll_timer(device)
end

local function info_changed(driver, device, event, args)
  ensure_poll_timer(driver, device)
  poll_once(driver, device)
end

-- ---------- capability handlers ----------

local function handle_refresh(driver, device, command)
  poll_once(driver, device)
end

local function handle_switch_on(driver, device, command)
  -- Read-only sensor semantics for v1: just refresh
  poll_once(driver, device)
end

local function handle_switch_off(driver, device, command)
  -- Read-only sensor semantics for v1: just refresh
  poll_once(driver, device)
end

-- Discovery: v1 只创建一个设备（靠 preference 配 IP/Port）
local function discovery_handler(driver, opts, continue)
  local dni = "pi-sound-sensor:v1"

  for _, d in ipairs(driver:get_devices()) do
    if d.device_network_id == dni then
      return
    end
  end

  driver:try_create_device({
    type = "LAN",
    device_network_id = dni,
    label = "Loud Event",
    profile = "pi-sound-sensor",
    manufacturer = "DIY",
    model = "PiUSBMic",
    vendor_provided_label = "Loud Event"
  })
end

local driver = Driver(DRIVER_NAME, {
  discovery = discovery_handler,
  lifecycle_handlers = {
    added = device_added,
    init = device_init,
    removed = device_removed,
    infoChanged = info_changed,
  },
  capability_handlers = {
    [capabilities.refresh.ID] = {
      [capabilities.refresh.commands.refresh.NAME] = handle_refresh
    },
    [capabilities.switch.ID] = {
      [capabilities.switch.commands.on.NAME] = handle_switch_on,
      [capabilities.switch.commands.off.NAME] = handle_switch_off
    }
  }
})

driver:run()
