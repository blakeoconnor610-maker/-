-- Coordination board for the two Claude sessions working in Team Create.
-- Read this before every task. Claim a task by setting owner and status = "working".
-- status: "open" | "working" | "done"
return {
	tasks = {
		{
			id = 1,
			title = "Obby course and progress (server)",
			owner = "Blake",
			status = "done",
			area = "ServerScriptService, Workspace",
			notes = "ServerScriptService/ObbyServer builds a 12-stage course in Workspace/Obby (jumps, lava path, moving platform, fading tiles), tracks leaderstats Stage/Wins, and saves them in a DataStore.",
		},
		{
			id = 2,
			title = "Obby HUD and finish screen (client)",
			owner = "Blake",
			status = "done",
			area = "StarterPlayer",
			notes = "StarterPlayer/StarterPlayerScripts/ObbyUI shows stage, progress bar, timer, a Restart button, checkpoint toasts, and a finish screen.",
		},
	},

	-- Asks for work in the other side's area.
	requests = {
		-- { from = "Blake", to = "<other name>", ask = "...", status = "open" },
	},

	-- Everything in ReplicatedStorage/Shared.
	interfaces = {
		{
			name = "Shared (attribute ObbyTotalStages)",
			kind = "Attribute",
			owner = "Blake",
			details = "Number of stages in the obby.",
		},
		{
			name = "Shared/Remotes/Finished",
			kind = "RemoteEvent",
			direction = "Server -> Client",
			args = "elapsedSeconds: number, wins: number, bestTime: number?",
			owner = "Blake",
		},
		{
			name = "Shared/Remotes/RequestRestart",
			kind = "RemoteEvent",
			direction = "Client -> Server",
			args = "none (sends the player back to stage 1 and restarts the timer)",
			owner = "Blake",
		},
		{
			name = "Player state",
			kind = "leaderstats + attributes",
			owner = "Blake",
			details = "leaderstats/Stage and leaderstats/Wins (IntValue); player attributes RunStartedAt (server time), Finished (boolean), BestTime (number?).",
		},
	},
}
