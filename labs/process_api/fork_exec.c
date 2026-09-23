#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    setbuf(stdout, NULL);

    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        return EXIT_FAILURE;
    }

    if (pid == 0) {
        printf("child: before exec\n");
        execl("./exec_target", "exec_target", (char *)NULL);
        perror("exec failed");
        return EXIT_FAILURE;
    }

    printf("parent: child created; parent continues\n");
    return EXIT_SUCCESS;
}
