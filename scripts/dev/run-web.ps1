$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$WebRoot = Join-Path $ProjectRoot "apps\web"

# 从 Web 包目录启动，确保 Vite 的 /api 代理和相对资源路径与 PyCharm、终端
# 中的行为一致。
& corepack pnpm --dir $WebRoot run dev
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
