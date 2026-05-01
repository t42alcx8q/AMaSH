### Attack Demo

Below are the 16 attack demos we conducted, marking from A1 -- A16.

#### Testbed

![testbed](./images/attack_demo/testbed.png)

![device_topo](./images/attack_demo/device_topo.png)

##### A1 

![A1-1](./images/attack_demo/A1-1.png)

![A1-2](./images/attack_demo/A1-2.png)

![A1-3](./images/attack_demo/A1-3.png)

![A1-4](./images/attack_demo/A1-4.png)

![A1-5](./images/attack_demo/A1-5.png)

![A1-6](./images/attack_demo/A1-6.png)

Victim(A): [C: no sounds for 2 hours + mode="away"] -> [A: arm the home]

Attacker(B): [T: A actually leaves home] -> [A: Play ambient "home sounds" (TV, conversation, kitchen sounds) on B's speaker in A's home] 

<u>Device: Google Nest smart speaker(12), Sound Sensor - Ras Pi (14)</u>



##### A2

![A2-1](./images/attack_demo/A2-1.png)

![A2-2](./images/attack_demo/A2-2.png)

Victim(A): [C: mode="away"] + [T: bedroom temperature > 24^\circ\text{C}] → [A: open window in the bedroom]

Attacker(B): [A: turn on the heater in the living room through the app]

<u>Device: 4-in-1 sensor(9), smart plug(3), SwitchBot Curtain Slider(15) (simulating the window opener)</u>



##### A3

![A3](./images/attack_demo/A3.png)

Victim(A): [T: motion detected in kitchen during 02:30–05:30] -> [A: siren ON]
Attacker(B): [C: after 23:30 ∧ siren = ON] -> [A: siren OFF]

<u>Device: motion sensor(11), smart siren(13)</u>

#### A4

![A4](./images/attack_demo/A4.png)

Attacker(B): [A: DisableRule(R_v)] (K=HomeKit)
<u>Device: sensor(7), smart siren(13)</u>

The attacker can disable the victim’s rule by:

- Disable the single rule through the single automation tab
- Disable the victim from adding and editing accessories



##### A5

![A5](./images/attack_demo/A5.png)

Victim(A): [T: door unlock] + [C: 2:00–06:00] -> [A: camera record]

Attacker: 

AO1 - 1:55 DisableRule(R_v)

AO2 - 06:05 EnableRule(R_v)



##### A6

![A6](./images/attack_demo/A6.png)

Victim(A): [T: porch light ON] + [C: mode=Away] -> [A: front camera record]

Dependency rule: [T: door unlock] -> [A: porch light ON]

Attacker: DisableRule(R_d)



##### A7

![A7](./images/attack_demo/A7.png)

Victim(A): [T: motion detected while mode=Away] -> [A: record + siren]
Attacker: AO_a: EditRule(replace action with siren only - do not record)
<u>Device: motion sensor(7), camera(1), siren(13)</u>



##### A8

![A8](./images/attack_demo/A8.png)

Victim(A): [T: 22:30] → [A: ActivateScene("Goodnight")]

Goodnight scene: lock all doors + system Night + enable camera

Attacker AO_a : [A: EditScene("Goodnight", remove: enable camera)]



##### A9

![A9](./images/attack_demo/A9.png)

Victim(A): [C: calendar shows "Owner at home" now] → [A: turn OFF indoor cameras for privacy]
Attacker AO_a : [A: WriteSharedCalendarEvent("Owner at home", 14:00–17:00)] (O=Calendar, K=GoogleCalendar)

<u>Device: Arlo camera(1), IFTTT</u>

- Victim (A): If the calendar event “Study at home (Zoom meeting with Eric)” and the event is started -> disable the indoor camera.

- Attacker (B): When A is not at home, B adds events to the shared calendar (e.g., “Study at home”) at times to disable A’s indoor camera.



##### A11

![A10-1](./images/attack_demo/A10-1.png)

![A10-2](./images/attack_demo/A10-2.png)

Victim(A): [T: entryway motion AND mode="Away"] → [A: alert Alice + start camera]
Attacker AO_a : [A: BindPlatform(entryway_motion_sensor, IFTTT)] (O=motion_sensor, K=SmartThings→IFTTT)
Attacker external rule: [T: motion detected] → [A: log to Google Sheets/webhook]

<u>Device: Presence Sensor FP2(18)</u>

Attacker(B): Set up a motion sensor near A’s bedroom door to track the daily pattern, i.e., when to come back to the bedroom or leave the bedroom



**A11 / A12**

![A12-1](./images/attack_demo/A12-1.png)

![A12-2](./images/attack_demo/A12-2.png)

Victim R_v: back home at night and unlock the door through the app
Attacker AO_a : [A: ChangeRole(victim, Admin→Member) + ToggleSettingsPermission(Alice, OFF)]

=> The victim cannot unlock the door through the app at all 

if and only if P_attacker > P_victim and the attacker is the home owner, change the roles of victim between [admin, authorized user] (while home owner >~ admin >> authorized user)

*home owner >~ admin means that while admin has the same device/routine access (CRUD the rules and remote control), admin cannot perform role AO on home owner, but home owner can do that to admins



##### A13

![A13](./images/attack_demo/A13.png)

- If and only if attacker \> victim and the attacker is the home owner, change the roles of victim between \[admin, authorized user\] (while home owner \>\~ admin\* \>\> authorized user)

  \*home owner \>\~ admin means that while admin has the same device/routine access (CRUD the rules and remote control), admin cannot perform role AO on home owner, but home owner can do that to admins

- The victim won’t get a notification 

Attacker: turn off the activity notifications in device settings  



##### A14

![A14](./images/attack_demo/A14.png)

Victim R_v : [T: front door opened after midnight] → [A: log event to HomeKit Activity]
Attacker AO_a : [A: ToggleLog(HomeKitActivity, off)] with \tau_a=01{:}00\text{–}02{:}00]
<u>Device: smart lock(10)</u>



##### A15

Victim: owns a Matter smart plug and sets it up on SmartThings

AO_a = [A: BindPlatform(smart_plug, K_ext = attacker_platform)] i.e., HomeKit

General way to share a matter device across different services:

![A15-1](./images/attack_demo/A15-1.png)

Direct setting up the device through the Matter QR code on the device (to HomeKit):

Observation: There is no notification given to the victim that the smart plug is connected to another platform

![A15-2](./images/attack_demo/A15-2.png)

On HomeKit, way to check whether the Matter plug is linked to other services:

![A15-3](./images/attack_demo/A15-3.png)



##### A16

#### ![A16-1](./images/attack_demo/A16-1.png)

![A16-2](./images/attack_demo/A16-2.png)

Victim's R_v: [T: entry detected motion] + [C: mode=home + 2:00 AM-6:00 AM] → [A: siren on]

Attacker AO_a :

AO1: [A: Create Automation with the same name but weaker action]:

1. Weak trigger: nobody at home
2. Weak action: turn on a plug in the kitchen
3. Delete the original automation
