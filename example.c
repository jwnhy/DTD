int a = 1;
int func() {
    int i;
    for (; i < 1; i++);
    if (a) {
        short b = 2; /* error point */
        { int i; }
    }
}
int main() { func(); }
