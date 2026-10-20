source("R/runtime.R")
stopifnot(runtime_port("3838") == 3838L, runtime_port("1024") == 1024L, runtime_port("65535") == 65535L)
for (value in list("", "80", "0", "65536", "-3838", "3.5", "+3838", " 3838", NA_character_, c("3838", "3839"), NULL, 3838)) {
  error <- tryCatch({ runtime_port(value); NULL }, error = identity)
  stopifnot(inherits(error, "error"), grepl("PORT must", conditionMessage(error), fixed = TRUE))
}
check_runtime()
cat("Runtime configuration tests passed\n")
