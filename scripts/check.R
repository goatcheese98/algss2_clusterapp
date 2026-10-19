source("scripts/dependencies.R")
check_dependencies()
files <- c("app.R", list.files("R", "\\.R$", full.names = TRUE), list.files("scripts", "\\.R$", full.names = TRUE), list.files("tests", "\\.R$", full.names = TRUE))
for (file in files) {
  parse(file = file)
  text <- readLines(file, warn = FALSE)
  if (any(grepl("[[:blank:]]+$", text))) stop(paste("Trailing whitespace:", file))
}
source("R/analysis.R")
if (requireNamespace("codetools", quietly = TRUE)) {
  codetools::checkUsageEnv(environment(analyze_players))
} else cat("codetools unavailable; usage analysis skipped (parse/whitespace lint still run).\n")
cat("R parse and read-only whitespace lint passed\n")
