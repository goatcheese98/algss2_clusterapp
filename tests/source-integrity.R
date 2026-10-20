source("scripts/source-integrity.R")
versions <- dget("scripts/package-versions.R")
lock <- read_source_lock(versions)
stopifnot(nrow(lock) == 72L, identical(lock$package, names(versions)))
expect_error <- function(expr) stopifnot(inherits(tryCatch({ force(expr); NULL }, error = identity), "error"))
file <- tempfile("source with spaces ")
writeBin(charToRaw("abc"), file)
# NIST's standard SHA-256 test vector; accepted bytes, then actual corruption.
abc <- "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
stopifnot(verify_source(file, abc))
writeBin(charToRaw("abd"), file)
expect_error(verify_source(file, abc))
expect_error(verify_source(file, "invalid"))
expect_error(read_source_lock(versions[-1]))
wrong <- versions; wrong[[1]] <- "999.0"
expect_error(read_source_lock(wrong))
for (kind in c("duplicate", "digest", "origin")) {
  bad <- lock
  if (kind == "duplicate") bad$package[2] <- bad$package[1]
  if (kind == "digest") bad$sha256[1] <- "broken"
  if (kind == "origin") bad$url[1] <- sub("https:", "http:", bad$url[1])
  path <- tempfile(); write.table(bad, path, sep = "\t", quote = FALSE, row.names = FALSE)
  expect_error(read_source_lock(versions, path)); unlink(path)
}
unlink(file)
cat("Source lock and corruption-rejection tests passed\n")
