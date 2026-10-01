param(
    [Parameter(Mandatory = $true)]
    [string]$HostName,

    [Parameter(Mandatory = $true)]
    [int]$Port,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$InstanceId,

    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$IdentityFile,

    [string]$UserName = "root",
    [string]$Ref = "main",
    [string]$RepositoryUrl = "https://github.com/ArchwingZeroThr/Reproduction4grade1.git",
    [string]$RemoteRoot = "/root/autodl-tmp/Reproduction4grade1"
)

$ErrorActionPreference = "Stop"

$sshTarget = "${UserName}@${HostName}"
$resolvedIdentityFile = (Resolve-Path -LiteralPath $IdentityFile).Path
$sshArgs = @(
    "-o", "BatchMode=yes",
    "-o", "StrictHostKeyChecking=accept-new",
    "-i", $resolvedIdentityFile,
    "-p", $Port,
    $sshTarget
)

$remoteScript = @"
set -euo pipefail
if [ ! -d '$RemoteRoot/.git' ]; then
  git clone --branch '$Ref' --single-branch '$RepositoryUrl' '$RemoteRoot'
else
  git -C '$RemoteRoot' fetch origin '$Ref'
  git -C '$RemoteRoot' checkout '$Ref'
  git -C '$RemoteRoot' pull --ff-only origin '$Ref'
fi
SIMDIFFREC_REMOTE_INSTANCE_ID='$InstanceId' \
  bash '$RemoteRoot/projects/SimDiffRec/scripts/autodl/bootstrap.sh' \
  '$RemoteRoot/projects/SimDiffRec'
"@

& ssh @sshArgs $remoteScript
if ($LASTEXITCODE -ne 0) {
    throw "AutoDL deployment failed with exit code $LASTEXITCODE"
}

Write-Output "AUTODL_DEPLOY_OK"
