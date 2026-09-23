#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    setbuf(stdout, NULL);

    printf("main: before fork\n");
    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        return EXIT_FAILURE;
    }

    if (pid == 0) {
        printf("child: fork returned 0\n");
    } else {
        printf("parent: fork returned child-pid=%ld\n", (long)pid);
    }

    printf("%s: after fork\n", pid == 0 ? "child" : "parent");
    return EXIT_SUCCESS;
}
