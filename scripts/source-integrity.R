# Setup-only source verification, using coreutils rather than bootstrapping R packages.
read_source_lock <- function(versions, path = "scripts/source-lock.tsv") {
  lock <- read.delim(path, colClasses = "character", check.names = FALSE)
  if (!identical(names(lock), c("package", "version", "sha256", "url")) ||
      anyNA(lock) || anyDuplicated(lock$package) ||
      !setequal(lock$package, names(versions)) ||
      any(!grepl("^[a-f0-9]{64}$", lock$sha256))) stop("Invalid source lock coverage or digest.")
  lock <- lock[match(names(versions), lock$package), , drop = FALSE]
  if (any(lock$version != unname(versions))) stop("Source lock version mismatch.")
  for (i in seq_len(nrow(lock))) {
    filename <- sprintf("%s_%s.tar.gz", lock$package[i], lock$version[i])
    allowed <- c(paste0("https://cran.r-project.org/src/contrib/", filename),
                 sprintf("https://cran.r-project.org/src/contrib/Archive/%s/%s", lock$package[i], filename))
    if (!lock$url[i] %in% allowed) stop("Unexpected source lock origin.")
  }
  if (!nzchar(Sys.which("sha256sum"))) stop("Setup requires coreutils sha256sum.")
  lock
}

verify_source <- function(path, expected) {
  if (length(expected) != 1L || is.na(expected) || !grepl("^[a-f0-9]{64}$", expected)) stop("Invalid expected source digest.")
  output <- system2("sha256sum", shQuote(path), stdout = TRUE, stderr = TRUE)
  if (!is.null(attr(output, "status")) || length(output) != 1L ||
      substr(output, 1L, 64L) != expected) stop(paste("Source SHA-256 mismatch:", basename(path)))
  invisible(TRUE)
}
