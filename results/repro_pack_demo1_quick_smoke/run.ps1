$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
if (Test-Path 'replay_outputs') { Remove-Item -Recurse -Force 'replay_outputs' }
py -m photonstrust.cli run 'config.yml' --output 'replay_outputs'
py 'verify.py' --bundle 'benchmark_bundle.json' --output 'replay_outputs'
