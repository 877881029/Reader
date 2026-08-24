function Resolve-SmokeFailure {
    [CmdletBinding()]
    param(
        [AllowNull()]
        [System.Management.Automation.ErrorRecord]$SmokeError,
        [string[]]$CleanupFailures = @()
    )

    $cleanup = @(
        $CleanupFailures |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if ($null -eq $SmokeError -and $cleanup.Count -eq 0) {
        return $null
    }
    if ($null -ne $SmokeError -and $cleanup.Count -eq 0) {
        return $SmokeError
    }

    $cleanupMessage = "Smoke cleanup failed: $($cleanup -join '; ')"
    if ($null -ne $SmokeError) {
        $message = "$($SmokeError.Exception.Message)`n$cleanupMessage"
        $errorId = "ReaderSmokeAndCleanupFailure"
        $target = $SmokeError.TargetObject
    } else {
        $message = $cleanupMessage
        $errorId = "ReaderSmokeCleanupFailure"
        $target = $null
    }
    $exception = [System.InvalidOperationException]::new($message)
    return [System.Management.Automation.ErrorRecord]::new(
        $exception,
        $errorId,
        [System.Management.Automation.ErrorCategory]::OperationStopped,
        $target
    )
}
