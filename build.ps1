

if(Test-Path -Path fountain_script)
{
    Remove-Item -path fountain_script -Recurse -Force
}

New-Item -ItemType directory -Path fountain_script

Copy-Item -Path .\__init__.py -Destination fountain_script
Copy-Item -Path .\fountain.py -Destination fountain_script
Copy-Item -Path .\README.md -Destination fountain_script
Copy-Item -Path '.\Rick&Steel.fountain' -Destination fountain_script
Copy-Item -Path .\TestFountain.blend -Destination fountain_script

$initScript = Get-Content .\__init__.py
$match = $initScript | Select-String '^.*\"version\".*:.*\(.*(\d+).*,.*(\d+).*,.*(\d+).*\).*$'  -AllMatches
if(!$match.Matches[0].Success ){
    Write-Error "Could not find version number"
    return 
}
$v0 = $match.Matches[0].Groups[1].Value
$v1 = $match.Matches[0].Groups[2].Value
$v2 = $match.Matches[0].Groups[3].Value
Write-Host "Writing version ${v0}-${v1}-${v2}"
$zipFileName = "fountain_script-${v0}-${v1}-${v2}.zip"

Compress-Archive -Path .\fountain_script -DestinationPath $zipFileName
