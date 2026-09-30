# Obby with UI

| File | Put it in Studio as |
|---|---|
| `ServerScriptService/ObbyServer.server.lua` | **Script** named `ObbyServer` in ServerScriptService |
| `StarterPlayerScripts/ObbyUI.client.lua` | **LocalScript** named `ObbyUI` in StarterPlayer > StarterPlayerScripts |
| `ServerStorage/_ClaudeSync/Board.lua` | **ModuleScript** named `Board` in ServerStorage > Folder `_ClaudeSync` |

The server script builds the whole course (`Workspace/Obby`) and creates
`ReplicatedStorage/Shared/Remotes` when the game runs, so nothing has to be built by hand.
Press Play to test.

To save progress, turn on Game Settings > Security > "Enable Studio Access to API Services".
Without it the obby still works, it just doesn't remember your stage.

Tweak `STAGE_COUNT`, `SEGMENT_LENGTH` and `RISE_PER_STAGE` at the top of `ObbyServer` to change the course.
