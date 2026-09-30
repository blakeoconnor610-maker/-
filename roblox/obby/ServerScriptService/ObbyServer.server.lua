-- ObbyServer
-- Builds the obby course in Workspace, tracks each player's stage, and saves progress.
--
-- Shared interface (ReplicatedStorage/Shared):
--   Attribute ObbyTotalStages (number) on the Shared folder
--   Remotes/Finished (RemoteEvent, server -> client): elapsedSeconds, wins, bestTime (number or nil)
--   Remotes/RequestRestart (RemoteEvent, client -> server): no args, sends the player back to stage 1
--
-- Player state (readable on the client):
--   leaderstats/Stage, leaderstats/Wins (IntValue)
--   Attributes RunStartedAt (server time), Finished (boolean), BestTime (number or nil)

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local DataStoreService = game:GetService("DataStoreService")

local STAGE_COUNT = 12
local START_POSITION = Vector3.new(0, 12, 60)
local SEGMENT_LENGTH = 40
local RISE_PER_STAGE = 3
local PAD_SIZE = Vector3.new(12, 1, 8)
local RESTART_COOLDOWN = 1
local LAVA_COLOR = Color3.fromRGB(255, 70, 40)

--== Shared interface ==--

local function getOrCreate(parent, className, name)
	local existing = parent:FindFirstChild(name)
	if existing then
		return existing
	end
	local instance = Instance.new(className)
	instance.Name = name
	instance.Parent = parent
	return instance
end

local sharedFolder = getOrCreate(ReplicatedStorage, "Folder", "Shared")
sharedFolder:SetAttribute("ObbyTotalStages", STAGE_COUNT)
local remotes = getOrCreate(sharedFolder, "Folder", "Remotes")
local finishedEvent = getOrCreate(remotes, "RemoteEvent", "Finished")
local restartEvent = getOrCreate(remotes, "RemoteEvent", "RequestRestart")

--== Course building ==--

local function makePart(name, size, cframe, color, material, parent)
	local part = Instance.new("Part")
	part.Name = name
	part.Size = size
	part.CFrame = cframe
	part.Color = color
	part.Material = material or Enum.Material.SmoothPlastic
	part.Anchored = true
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	part.Parent = parent
	return part
end

local function addLabel(part, text)
	local gui = Instance.new("SurfaceGui")
	gui.Face = Enum.NormalId.Top
	gui.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
	gui.PixelsPerStud = 40
	local label = Instance.new("TextLabel")
	label.Size = UDim2.fromScale(1, 1)
	label.BackgroundTransparency = 1
	label.Text = text
	label.TextScaled = true
	label.Font = Enum.Font.GothamBold
	label.TextColor3 = Color3.new(1, 1, 1)
	label.TextStrokeTransparency = 0.4
	label.Parent = gui
	gui.Parent = part
end

local function makeKillPart(name, size, cframe, parent)
	local part = makePart(name, size, cframe, LAVA_COLOR, Enum.Material.Neon, parent)
	part.Touched:Connect(function(hit)
		local humanoid = hit.Parent and hit.Parent:FindFirstChildOfClass("Humanoid")
		if humanoid and humanoid.Health > 0 then
			humanoid.Health = 0
		end
	end)
	return part
end

-- Each obstacle builder fills the gap between point a (end of one checkpoint pad)
-- and point b (start of the next one).

local movers = {}

local function buildJumps(parent, a, b, color)
	local steps = 4
	for step = 1, steps do
		local t = step / (steps + 1)
		local side = if step % 2 == 0 then 3 else -3
		local position = a:Lerp(b, t) + Vector3.new(side, 0, 0)
		makePart("Jump" .. step, Vector3.new(4, 1, 4), CFrame.new(position), color, nil, parent)
	end
end

local function buildLavaPath(parent, a, b, color)
	local length = (b - a).Magnitude
	makePart("Walkway", Vector3.new(6, 1, length), CFrame.lookAt(a:Lerp(b, 0.5), b), color, nil, parent)
	for index, t in { 0.25, 0.5, 0.75 } do
		local stripCFrame = CFrame.lookAt(a:Lerp(b, t), b) * CFrame.new(0, 0.6, 0)
		makeKillPart("LavaStrip" .. index, Vector3.new(6.2, 0.2, 2), stripCFrame, parent)
	end
end

local function buildMover(parent, a, b, color)
	local platform = makePart("MovingPlatform", Vector3.new(8, 1, 8), CFrame.new(a:Lerp(b, 0.5)), color, nil, parent)
	table.insert(movers, { part = platform, a = a, b = b, speed = 1.2 })
end

local function buildFadingTiles(parent, a, b, color)
	local tiles = 5
	for index = 1, tiles do
		local t = index / (tiles + 1)
		local tile = makePart("FadingTile" .. index, Vector3.new(5, 1, 4), CFrame.new(a:Lerp(b, t)), color, Enum.Material.Glass, parent)
		local fading = false
		tile.Touched:Connect(function(hit)
			if fading or not Players:GetPlayerFromCharacter(hit.Parent) then
				return
			end
			fading = true
			task.wait(0.6)
			tile.Transparency = 0.8
			tile.CanCollide = false
			task.wait(2)
			tile.Transparency = 0
			tile.CanCollide = true
			fading = false
		end)
	end
end

local builders = { buildJumps, buildLavaPath, buildMover, buildFadingTiles }

local function padPosition(stage)
	return START_POSITION + Vector3.new(0, (stage - 1) * RISE_PER_STAGE, (stage - 1) * SEGMENT_LENGTH)
end

local oldCourse = workspace:FindFirstChild("Obby")
if oldCourse then
	oldCourse:Destroy()
end

local course = Instance.new("Model")
course.Name = "Obby"

local checkpoints = {}
local halfPad = Vector3.new(0, 0, PAD_SIZE.Z / 2)

for stage = 1, STAGE_COUNT do
	local stageModel = Instance.new("Model")
	stageModel.Name = "Stage" .. stage
	stageModel.Parent = course

	local pad = makePart("Checkpoint", PAD_SIZE, CFrame.new(padPosition(stage)), Color3.fromRGB(235, 235, 235), nil, stageModel)
	pad:SetAttribute("Stage", stage)
	addLabel(pad, "Stage " .. stage)
	checkpoints[stage] = pad

	local color = Color3.fromHSV((stage - 1) / STAGE_COUNT, 0.55, 0.95)
	local builder = builders[(stage - 1) % #builders + 1]
	builder(stageModel, padPosition(stage) + halfPad, padPosition(stage + 1) - halfPad, color)
end

local finishPad = makePart(
	"Finish",
	Vector3.new(16, 1, 12),
	CFrame.new(padPosition(STAGE_COUNT + 1) + Vector3.new(0, 0, 2)),
	Color3.fromRGB(255, 205, 60),
	Enum.Material.Neon,
	course
)
addLabel(finishPad, "FINISH")

local firstZ = START_POSITION.Z - PAD_SIZE.Z
local lastZ = padPosition(STAGE_COUNT + 1).Z + 12
makeKillPart(
	"LavaFloor",
	Vector3.new(80, 1, lastZ - firstZ),
	CFrame.new(START_POSITION.X, START_POSITION.Y - 10, (firstZ + lastZ) / 2),
	course
)

course.Parent = workspace

-- Anchored platforms are moved by CFrame; setting AssemblyLinearVelocity too
-- makes them carry players standing on them.
RunService.Heartbeat:Connect(function()
	local now = os.clock()
	for _, mover in movers do
		local t = 0.5 + 0.3 * math.sin(now * mover.speed)
		mover.part.CFrame = CFrame.new(mover.a:Lerp(mover.b, t))
		mover.part.AssemblyLinearVelocity = (mover.b - mover.a) * (0.3 * mover.speed * math.cos(now * mover.speed))
	end
end)

--== Player progress ==--

local progressStore
do
	local ok, result = pcall(DataStoreService.GetDataStore, DataStoreService, "ObbyProgress_v1")
	if ok then
		progressStore = result
	else
		warn("[ObbyServer] DataStore unavailable, progress will not save: " .. tostring(result))
	end
end

local lastRestart = {}

local function getStats(player)
	local leaderstats = player:FindFirstChild("leaderstats")
	if not leaderstats then
		return nil, nil
	end
	return leaderstats:FindFirstChild("Stage"), leaderstats:FindFirstChild("Wins")
end

local function sendToCheckpoint(player, character)
	local stageValue = getStats(player)
	local root = character:WaitForChild("HumanoidRootPart", 10)
	if not stageValue or not root then
		return
	end
	local pad = checkpoints[math.clamp(stageValue.Value, 1, STAGE_COUNT)]
	task.wait() -- let the default spawn finish first
	if character.Parent then
		character:PivotTo(pad.CFrame + Vector3.new(0, 4, 0))
	end
end

local function saveProgress(player)
	if not progressStore then
		return
	end
	local stageValue, winsValue = getStats(player)
	if not stageValue or not winsValue then
		return
	end
	local data = {
		stage = stageValue.Value,
		wins = winsValue.Value,
		bestTime = player:GetAttribute("BestTime"),
	}
	local ok, err = pcall(progressStore.SetAsync, progressStore, "player_" .. player.UserId, data)
	if not ok then
		warn("[ObbyServer] Failed to save " .. player.Name .. ": " .. tostring(err))
	end
end

local function onPlayerAdded(player)
	local leaderstats = Instance.new("Folder")
	leaderstats.Name = "leaderstats"
	local stageValue = Instance.new("IntValue")
	stageValue.Name = "Stage"
	stageValue.Value = 1
	stageValue.Parent = leaderstats
	local winsValue = Instance.new("IntValue")
	winsValue.Name = "Wins"
	winsValue.Parent = leaderstats
	leaderstats.Parent = player

	player:SetAttribute("RunStartedAt", workspace:GetServerTimeNow())
	player:SetAttribute("Finished", false)
	player:SetAttribute("RunFromStart", true)

	player.CharacterAdded:Connect(function(character)
		sendToCheckpoint(player, character)
	end)
	if player.Character then
		task.spawn(sendToCheckpoint, player, player.Character)
	end

	if not progressStore then
		return
	end
	local ok, data = pcall(progressStore.GetAsync, progressStore, "player_" .. player.UserId)
	if not ok then
		warn("[ObbyServer] Failed to load " .. player.Name .. ": " .. tostring(data))
		return
	end
	if type(data) == "table" then
		stageValue.Value = math.clamp(tonumber(data.stage) or 1, 1, STAGE_COUNT)
		winsValue.Value = tonumber(data.wins) or 0
		if type(data.bestTime) == "number" then
			player:SetAttribute("BestTime", data.bestTime)
		end
		-- A resumed run does not count toward the best time.
		player:SetAttribute("RunFromStart", stageValue.Value == 1)
	end
	if player.Parent and player.Character then
		task.spawn(sendToCheckpoint, player, player.Character)
	end
end

for stage, pad in checkpoints do
	pad.Touched:Connect(function(hit)
		local player = Players:GetPlayerFromCharacter(hit.Parent)
		local stageValue = player and getStats(player)
		if stageValue and stage > stageValue.Value then
			stageValue.Value = stage
		end
	end)
end

finishPad.Touched:Connect(function(hit)
	local player = Players:GetPlayerFromCharacter(hit.Parent)
	if not player or player:GetAttribute("Finished") then
		return
	end
	local stageValue, winsValue = getStats(player)
	if not stageValue or not winsValue or stageValue.Value < STAGE_COUNT then
		return
	end

	player:SetAttribute("Finished", true)
	local now = workspace:GetServerTimeNow()
	local elapsed = now - (player:GetAttribute("RunStartedAt") or now)
	winsValue.Value += 1

	local best = player:GetAttribute("BestTime")
	if player:GetAttribute("RunFromStart") and (not best or elapsed < best) then
		best = elapsed
		player:SetAttribute("BestTime", best)
	end
	finishedEvent:FireClient(player, elapsed, winsValue.Value, best)
end)

restartEvent.OnServerEvent:Connect(function(player)
	local now = os.clock()
	if lastRestart[player] and now - lastRestart[player] < RESTART_COOLDOWN then
		return
	end
	lastRestart[player] = now

	local stageValue = getStats(player)
	if not stageValue then
		return
	end
	stageValue.Value = 1
	player:SetAttribute("Finished", false)
	player:SetAttribute("RunFromStart", true)
	player:SetAttribute("RunStartedAt", workspace:GetServerTimeNow())
	player:LoadCharacter()
end)

Players.PlayerAdded:Connect(onPlayerAdded)
for _, player in Players:GetPlayers() do
	task.spawn(onPlayerAdded, player)
end

Players.PlayerRemoving:Connect(function(player)
	saveProgress(player)
	lastRestart[player] = nil
end)

game:BindToClose(function()
	for _, player in Players:GetPlayers() do
		saveProgress(player)
	end
end)
