function Test-DockerRunning {
    $DockerCommand = (Get-Command docker.exe -ErrorAction SilentlyContinue).Source
    if (-not $DockerCommand) {
        return $false
    }
    $Probe = Start-Process -FilePath $DockerCommand -ArgumentList @("info") -WindowStyle Hidden -PassThru
    if (-not $Probe.WaitForExit(4000)) {
        Stop-Process -Id $Probe.Id -Force -ErrorAction SilentlyContinue
        return $false
    }
    return $Probe.ExitCode -eq 0
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Description
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Stop-ProcessTree {
    # Force-kill a process AND all of its descendants. Critical for uvicorn --reload,
    # whose reload *worker* (a multiprocessing spawn child) is the process that binds
    # the port — killing only the parent leaves that worker holding the socket.
    param([int]$ProcessId)
    if ($ProcessId -le 4) { return }          # never touch System/Idle (PID 0/4)
    if ($ProcessId -eq $PID) { return }        # never kill ourselves
    & taskkill.exe /PID $ProcessId /T /F *> $null
    # taskkill returns 128 when the process is already gone; that is expected during
    # our retry loop, so don't leak a non-zero exit code to the caller's $LASTEXITCODE.
    $global:LASTEXITCODE = 0
}

function Get-PortOwningProcessIds {
    # Every real process (PID > 4) that owns a socket on the port, in any state.
    param([int]$Port)
    $owners = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Where-Object { $_.OwningProcess -and [int]$_.OwningProcess -gt 4 } |
        Select-Object -ExpandProperty OwningProcess -Unique
    return @($owners | ForEach-Object { [int]$_ })
}

function Test-PortListening {
    param([int]$Port)
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Stop-AgroVisionApiProcesses {
    param(
        [int]$Port = 8765
    )

    # Anchor on the process that ACTUALLY owns the port (authoritative — no fuzzy
    # command-line matching that could hit an unrelated shell or editor). The reported
    # owner can be MISLEADING with uvicorn --reload: the reloader creates the listening
    # socket and hands it to a worker child by handle inheritance, so once the reloader
    # dies the socket is still reported under that dead PID while a live child worker
    # actually holds it. So for each owner we tree-kill the owner AND its children (the
    # inherited-socket worker), which also stops the reloader from respawning a worker.
    # Retry, because an orphaned worker can linger for a moment.
    $deadline = (Get-Date).AddSeconds(15)
    do {
        $targets = @{}
        foreach ($ownerId in (Get-PortOwningProcessIds -Port $Port)) {
            $targets[$ownerId] = $true
            $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ownerId" -ErrorAction SilentlyContinue
            foreach ($child in $children) {
                $targets[[int]$child.ProcessId] = $true
            }
        }
        foreach ($targetId in $targets.Keys) {
            Stop-ProcessTree -ProcessId $targetId
        }
        if (-not (Test-PortListening -Port $Port)) {
            return
        }
        Start-Sleep -Milliseconds 400
    } while ((Get-Date) -lt $deadline)

    # Still occupied — say exactly who holds it so the user can act, instead of a bare
    # failure. (A non-Listen TIME_WAIT socket would already have returned above.)
    $holders = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object {
            $proc = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
            $name = if ($proc) { $proc.ProcessName } else { "unknown" }
            "PID $($_.OwningProcess) ($name)"
        } | Sort-Object -Unique
    throw ("Port $Port is still occupied by: " + ($holders -join ', ') +
        ". Close it manually with: taskkill /F /T /PID <pid>  then re-run scripts\dev.ps1.")
}

function Wait-AgroVisionApi {
    param(
        [string]$Url = "http://127.0.0.1:8765",
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $openApi = Invoke-RestMethod "$Url/openapi.json" -TimeoutSec 3
            if ($openApi.paths.PSObject.Properties.Name -contains "/api/v1/cases") {
                return
            }
        } catch {
            # The process may still be importing the ONNX runtimes.
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)

    throw "AgroVision API did not expose /api/v1/cases within $TimeoutSeconds seconds."
}
