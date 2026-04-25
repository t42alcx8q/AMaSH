local cosock = require "cosock"
local http = cosock.asyncify "socket.http"
local ltn12 = require "ltn12"
local json = require "st.json"
local log = require "log"

local M = {}

local function parse_http_code(code, status)
  if type(code) == "number" then return code end
  if type(code) == "string" then
    local n = tonumber(code)
    if n then return n end
    local m = code:match("(%d%d%d)")
    if m then return tonumber(m) end
  end
  if type(status) == "string" then
    local m = status:match("(%d%d%d)")
    if m then return tonumber(m) end
  end
  return nil
end

function M.get_json(host, port, path, timeout_s)
  if not host or host == "" then
    return nil, "empty host"
  end
  if not port then
    return nil, "empty port"
  end
  path = path or "/state"
  timeout_s = timeout_s or 2

  -- socket.http supports TIMEOUT as a module global (best-effort)
  http.TIMEOUT = timeout_s

  local url = string.format("http://%s:%d%s", host, port, path)
  local chunks = {}

  local _, code, headers, status = http.request({
    url = url,
    method = "GET",
    headers = {
      ["Accept"] = "application/json",
      ["Connection"] = "close"
    },
    sink = ltn12.sink.table(chunks),
  })

  local http_code = parse_http_code(code, status)
  if http_code ~= 200 then
    return nil, string.format("http %s (%s) url=%s", tostring(http_code), tostring(status), url)
  end

  local body = table.concat(chunks)
  if not body or body == "" then
    return nil, "empty body"
  end

  local ok, data = pcall(json.decode, body)
  if not ok then
    log.warn(string.format("JSON decode failed: %s body=%s", tostring(data), body))
    return nil, "json decode failed"
  end

  return data, nil
end

return M
