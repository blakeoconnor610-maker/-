-- ObbyUI
-- Builds the obby HUD: stage counter, progress bar, run timer, restart button,
-- checkpoint toasts, and the finish screen. Uses the interface documented in ObbyServer.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local player = Players.LocalPlayer
local sharedFolder = ReplicatedStorage:WaitForChild("Shared")
local remotes = sharedFolder:WaitForChild("Remotes")
local finishedEvent = remotes:WaitForChild("Finished")
local restartEvent = remotes:WaitForChild("RequestRestart")
local stageValue = player:WaitForChild("leaderstats"):WaitForChild("Stage")

local FONT = Enum.Font.GothamBold
local WHITE = Color3.new(1, 1, 1)
local PANEL_COLOR = Color3.fromRGB(20, 22, 30)
local ACCENT = Color3.fromRGB(90, 200, 120)
local BUTTON_COLOR = Color3.fromRGB(60, 64, 80)

local function create(className, props, children)
	local instance = Instance.new(className)
	for key, value in props do
		instance[key] = value
	end
	for _, child in children or {} do
		child.Parent = instance
	end
	return instance
end

local function corner(radius)
	return create("UICorner", { CornerRadius = UDim.new(0, radius) })
end

local function formatTime(seconds)
	seconds = math.max(0, seconds)
	local minutes = math.floor(seconds / 60)
	return string.format("%d:%05.2f", minutes, seconds - minutes * 60)
end

local function makeButton(name, text, color)
	return create("TextButton", {
		Name = name,
		Text = text,
		Font = FONT,
		TextSize = 18,
		TextColor3 = WHITE,
		BackgroundColor3 = color,
		AutoButtonColor = true,
	}, { corner(8) })
end

--== HUD ==--

local screen = create("ScreenGui", {
	Name = "ObbyHUD",
	ResetOnSpawn = false,
	ZIndexBehavior = Enum.ZIndexBehavior.Sibling,
})

local stageLabel = create("TextLabel", {
	Name = "StageLabel",
	BackgroundTransparency = 1,
	Position = UDim2.fromOffset(14, 8),
	Size = UDim2.new(0.6, -14, 0, 26),
	Font = FONT,
	TextSize = 22,
	TextColor3 = WHITE,
	TextXAlignment = Enum.TextXAlignment.Left,
	Text = "Stage 1",
})

local timerLabel = create("TextLabel", {
	Name = "TimerLabel",
	BackgroundTransparency = 1,
	Position = UDim2.new(0.6, 0, 0, 8),
	Size = UDim2.new(0.4, -14, 0, 26),
	Font = Enum.Font.RobotoMono,
	TextSize = 20,
	TextColor3 = WHITE,
	TextXAlignment = Enum.TextXAlignment.Right,
	Text = "0:00.00",
})

local progressFill = create("Frame", {
	Name = "Fill",
	Size = UDim2.fromScale(0, 1),
	BackgroundColor3 = ACCENT,
	BorderSizePixel = 0,
}, { corner(4) })

local progressBar = create("Frame", {
	Name = "ProgressBar",
	Position = UDim2.new(0, 14, 1, -20),
	Size = UDim2.new(1, -28, 0, 8),
	BackgroundColor3 = BUTTON_COLOR,
	BorderSizePixel = 0,
}, { corner(4), progressFill })

local panel = create("Frame", {
	Name = "StagePanel",
	AnchorPoint = Vector2.new(0.5, 0),
	Position = UDim2.new(0.5, 0, 0, 10),
	Size = UDim2.fromOffset(280, 64),
	BackgroundColor3 = PANEL_COLOR,
	BackgroundTransparency = 0.15,
}, {
	corner(10),
	create("UIStroke", { Color = WHITE, Transparency = 0.85, Thickness = 1 }),
	stageLabel,
	timerLabel,
	progressBar,
})
panel.Parent = screen

local restartButton = makeButton("RestartButton", "Restart", BUTTON_COLOR)
restartButton.AnchorPoint = Vector2.new(1, 0)
restartButton.Position = UDim2.new(1, -12, 0, 10)
restartButton.Size = UDim2.fromOffset(110, 36)
restartButton.Parent = screen

local toast = create("TextLabel", {
	Name = "Toast",
	AnchorPoint = Vector2.new(0.5, 0),
	Position = UDim2.new(0.5, 0, 0, 84),
	Size = UDim2.fromOffset(260, 36),
	BackgroundColor3 = ACCENT,
	BackgroundTransparency = 1,
	Font = FONT,
	TextSize = 20,
	TextColor3 = WHITE,
	TextTransparency = 1,
	Text = "",
}, { corner(8) })
toast.Parent = screen

--== Finish screen ==--

local finishTitle = create("TextLabel", {
	BackgroundTransparency = 1,
	Position = UDim2.fromOffset(0, 18),
	Size = UDim2.new(1, 0, 0, 40),
	Font = FONT,
	TextSize = 32,
	TextColor3 = Color3.fromRGB(255, 205, 60),
	Text = "You finished!",
})

local finishTime = create("TextLabel", {
	BackgroundTransparency = 1,
	Position = UDim2.fromOffset(0, 66),
	Size = UDim2.new(1, 0, 0, 30),
	Font = Enum.Font.RobotoMono,
	TextSize = 24,
	TextColor3 = WHITE,
	Text = "",
})

local finishStats = create("TextLabel", {
	BackgroundTransparency = 1,
	Position = UDim2.fromOffset(0, 100),
	Size = UDim2.new(1, 0, 0, 24),
	Font = FONT,
	TextSize = 18,
	TextColor3 = Color3.fromRGB(190, 195, 210),
	Text = "",
})

local playAgainButton = makeButton("PlayAgainButton", "Play again", ACCENT)
playAgainButton.Position = UDim2.new(0, 20, 1, -60)
playAgainButton.Size = UDim2.new(0.5, -30, 0, 40)

local closeButton = makeButton("CloseButton", "Keep exploring", BUTTON_COLOR)
closeButton.Position = UDim2.new(0.5, 10, 1, -60)
closeButton.Size = UDim2.new(0.5, -30, 0, 40)

local finishCard = create("Frame", {
	Name = "Card",
	AnchorPoint = Vector2.new(0.5, 0.5),
	Position = UDim2.fromScale(0.5, 0.5),
	Size = UDim2.fromOffset(340, 220),
	BackgroundColor3 = PANEL_COLOR,
}, {
	corner(14),
	create("UIStroke", { Color = WHITE, Transparency = 0.8, Thickness = 1 }),
	finishTitle,
	finishTime,
	finishStats,
	playAgainButton,
	closeButton,
})

local overlay = create("Frame", {
	Name = "FinishScreen",
	Size = UDim2.fromScale(1, 1),
	BackgroundColor3 = Color3.new(0, 0, 0),
	BackgroundTransparency = 0.45,
	Visible = false,
	ZIndex = 10,
}, { finishCard })
overlay.Parent = screen

screen.Parent = player:WaitForChild("PlayerGui")

--== Behavior ==--

local toastTween
local function showToast(text)
	if toastTween then
		toastTween:Cancel()
	end
	toast.Text = text
	toast.TextTransparency = 0
	toast.BackgroundTransparency = 0.2
	toastTween = TweenService:Create(
		toast,
		TweenInfo.new(0.6, Enum.EasingStyle.Quad, Enum.EasingDirection.In, 0, false, 1.4),
		{ TextTransparency = 1, BackgroundTransparency = 1 }
	)
	toastTween:Play()
end

local function refreshStage()
	local total = sharedFolder:GetAttribute("ObbyTotalStages") or stageValue.Value
	stageLabel.Text = string.format("Stage %d / %d", stageValue.Value, total)
	local progress = if player:GetAttribute("Finished") then 1 else (stageValue.Value - 1) / total
	TweenService:Create(progressFill, TweenInfo.new(0.3), { Size = UDim2.fromScale(progress, 1) }):Play()
end

local lastStage = stageValue.Value
stageValue.Changed:Connect(function(newStage)
	if newStage > lastStage then
		showToast("Checkpoint! Stage " .. newStage)
	end
	lastStage = newStage
	refreshStage()
end)
sharedFolder:GetAttributeChangedSignal("ObbyTotalStages"):Connect(refreshStage)
player:GetAttributeChangedSignal("Finished"):Connect(refreshStage)
refreshStage()

RunService.RenderStepped:Connect(function()
	if player:GetAttribute("Finished") then
		return
	end
	local startedAt = player:GetAttribute("RunStartedAt")
	if startedAt then
		timerLabel.Text = formatTime(workspace:GetServerTimeNow() - startedAt)
	end
end)

finishedEvent.OnClientEvent:Connect(function(elapsed, wins, best)
	timerLabel.Text = formatTime(elapsed)
	finishTime.Text = "Time: " .. formatTime(elapsed)
	finishStats.Text = string.format("Wins: %d    Best: %s", wins, if best then formatTime(best) else "--")
	overlay.Visible = true
end)

local function restart()
	overlay.Visible = false
	restartEvent:FireServer()
end

restartButton.Activated:Connect(restart)
playAgainButton.Activated:Connect(restart)
closeButton.Activated:Connect(function()
	overlay.Visible = false
end)
