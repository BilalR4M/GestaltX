param(
    [Parameter(Mandatory = $true)][string]$TaskId,
    [Parameter(Mandatory = $true)][string]$Message,
    [string]$Owner = "bilal",
    [string[]]$Files = @()
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$TimelinePath = Join-Path $Root ".gestaltx/timeline.yaml"
$TeamPath = Join-Path $Root ".gestaltx/team.yaml"
$ProgressPath = Join-Path $Root ".gestaltx/progress.json"

if (-not (Test-Path $TimelinePath) -or -not (Test-Path $TeamPath)) {
    throw "Missing .gestaltx/timeline.yaml or team.yaml."
}

$Timeline = Get-Content $TimelinePath -Raw
$Team = Get-Content $TeamPath -Raw
if ($Timeline -notmatch [regex]::Escape($TaskId)) {
    throw "Task '$TaskId' is not present in timeline.yaml."
}

$MemberPattern = "(?ms)^\s{2}$([regex]::Escape($Owner)):\s.*?^\s{4}git:\s*^\s{6}name:\s*(?<name>[^\r\n]+)\s*^\s{6}email:\s*(?<email>[^\r\n]+)"
$Member = [regex]::Match($Team, $MemberPattern)
if (-not $Member.Success) {
    throw "Owner '$Owner' or git identity was not found in team.yaml."
}

$TaskPattern = "(?ms)-\s+id:\s*$([regex]::Escape($TaskId))\s*(?<body>.*?)(?=^\s*-\s+id:|\z)"
$Task = [regex]::Match($Timeline, $TaskPattern)
$DateMatch = [regex]::Match($Task.Groups["body"].Value, 'date:\s*"?(?<date>\d{4}-\d{2}-\d{2})')
$TimeMatch = [regex]::Match($Task.Groups["body"].Value, 'time:\s*"?(?<time>\d{2}:\d{2}:\d{2})')
if (-not $DateMatch.Success) {
    throw "Task '$TaskId' has no date."
}
$Time = if ($TimeMatch.Success) { $TimeMatch.Groups["time"].Value } else { "12:00:00" }
$CommitDate = "$($DateMatch.Groups["date"].Value)T${Time}+05:30"

$env:GIT_AUTHOR_NAME = $Member.Groups["name"].Value.Trim()
$env:GIT_AUTHOR_EMAIL = $Member.Groups["email"].Value.Trim()
$env:GIT_COMMITTER_NAME = $env:GIT_AUTHOR_NAME
$env:GIT_COMMITTER_EMAIL = $env:GIT_AUTHOR_EMAIL
$env:GIT_AUTHOR_DATE = $CommitDate
$env:GIT_COMMITTER_DATE = $CommitDate

Push-Location $Root
try {
    if ($Files.Count -gt 0) {
        git add -- $Files
    }
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        throw "No staged changes. Pass -Files or stage files first."
    }
    git commit -m $Message
    if ($LASTEXITCODE -ne 0) {
        throw "git commit failed."
    }
    $Commit = (git rev-parse HEAD).Trim()

    $Progress = if (Test-Path $ProgressPath) {
        Get-Content $ProgressPath -Raw | ConvertFrom-Json
    } else {
        [pscustomobject]@{ project = "GestaltX"; completed = @() }
    }
    $Completed = @($Progress.completed) + [pscustomobject]@{
        task_id = $TaskId
        commit = $Commit
        owner = $Owner
        date = $CommitDate
        message = $Message
    }
    $Progress.completed = $Completed
    $Progress.current_task_id = $null
    $Progress.last_updated = (Get-Date).ToString("o")
    $Progress | ConvertTo-Json -Depth 8 | Set-Content $ProgressPath -Encoding utf8
    Write-Host "Committed $TaskId as $Commit and updated progress.json."
}
finally {
    Pop-Location
    Remove-Item Env:GIT_AUTHOR_NAME, Env:GIT_AUTHOR_EMAIL, Env:GIT_COMMITTER_NAME,
        Env:GIT_COMMITTER_EMAIL, Env:GIT_AUTHOR_DATE, Env:GIT_COMMITTER_DATE -ErrorAction SilentlyContinue
}
