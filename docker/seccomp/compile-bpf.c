#include <errno.h>
#include <seccomp.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char** argv) {
	FILE* txt;
	FILE* bpf;
	char* line_buf = NULL;
	size_t line_buf_len = 0;
	ssize_t line_len;
	int syscall;
	scmp_filter_ctx filter_ctx;

	if (argc != 3) {
		fprintf(stderr, "Usage: %s input-file.txt output-file.bpf\n", argv[0]);
		exit(EXIT_FAILURE);
	}

	filter_ctx = seccomp_init(SCMP_ACT_KILL);

	txt = fopen(argv[1], "r");
	if (txt == NULL) {
		perror("Failed to open input file");
		exit(EXIT_FAILURE);
	}

	while (1) {
		line_len = getline(&line_buf, &line_buf_len, txt);
		if (line_len == -1) {
			if (errno != 0) {
				perror("Failed to read line from input file");
				exit(EXIT_FAILURE);
			}
			break;
		}

		if (line_len == 0) {
			continue; // empty line
		}
		if (line_buf[0] == '#') {
			continue; // "comment" line
		}

		if (line_buf[line_len - 1] == '\n') {
			// null-terminate the syscall, so we can look it up
			line_buf[line_len - 1] = '\0';
		}
		syscall = seccomp_syscall_resolve_name_arch(SCMP_ARCH_X86_64, line_buf);
		if (syscall == __NR_SCMP_ERROR) {
			fprintf(stderr, "Could not resolve syscall '%s'; skipping\n", line_buf);
			continue;
		}

		if (seccomp_rule_add(filter_ctx, SCMP_ACT_ALLOW, syscall, 0) != 0) {
			fprintf(stderr, "Error adding rule to allow '%s'\n", line_buf);
			exit(EXIT_FAILURE);
		}
	}
	if (line_buf != NULL) free(line_buf);

	if (fclose(txt) != 0) {
		perror("Failed to close input file");
		exit(EXIT_FAILURE);
	}

	bpf = fopen(argv[2], "w");
	if (bpf == NULL) {
		perror("Failed to open output file");
		exit(EXIT_FAILURE);
	}

	if (seccomp_export_pfc(filter_ctx, fileno(stdout)) != 0) {
		perror("Could not output PFC (debug info)");
		exit(EXIT_FAILURE);
	}

	if (seccomp_export_bpf(filter_ctx, fileno(bpf)) != 0) {
		perror("Failed to export BPF filter");
		exit(EXIT_FAILURE);
	}

	if (fclose(bpf) != 0) {
		perror("Failed to close output file");
		exit(EXIT_FAILURE);
	}

	seccomp_release(filter_ctx);
}
