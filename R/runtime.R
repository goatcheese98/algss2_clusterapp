# Startup boundary only. Analysis and filtering are deliberately unchanged.
runtime_port <- function(value = Sys.getenv("PORT", unset = "3838")) {
  if (!is.character(value) || length(value) != 1L || is.na(value) ||
      !grepl("^[0-9]{1,5}$", value)) stop("PORT must be a whole number from 1024 to 65535.")
  port <- as.integer(value)
  if (port < 1024L || port > 65535L) stop("PORT must be a whole number from 1024 to 65535.")
  port
}
check_runtime <- function() {
  if (getRversion() != numeric_version("4.5.0")) stop("The runtime requires R 4.5.0.")
  versions <- dget("scripts/package-versions.R")
  matches <- vapply(names(versions), function(pkg) {
    tryCatch(utils::packageVersion(pkg) == numeric_version(versions[[pkg]]), error = function(e) FALSE)
  }, logical(1))
  if (any(!matches)) stop(paste("Pinned runtime dependency mismatch:", paste(names(versions)[!matches], collapse = ", ")))
  invisible(TRUE)
}
# HTTP readiness on loopback, independent of proxy environment and extra tools.
# The HTTP probe complements, rather than substitutes for, WebSocket/browser tests.
check_readiness <- function(port = runtime_port()) {
  connection <- socketConnection(host = "127.0.0.1", port = port, open = "r+b", blocking = TRUE, timeout = 2)
  on.exit(close(connection))
  writeChar("GET / HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n", connection, eos = NULL, useBytes = TRUE)
  response <- readLines(connection, n = 2000, warn = FALSE)
  if (!length(response) || !grepl("^HTTP/1\\.[01] 200( |$)", response[1]) ||
      !any(grepl("shiny-javascript", response, fixed = TRUE)) ||
      !any(grepl("ALGS", response, fixed = TRUE))) stop("The ALGS Shiny page is not ready.")
  invisible(TRUE)
}
