#include <stdio.h>
#include <stdlib.h>

typedef struct node { int value; struct node *next; } Node;

static int push_front(Node **head, int v) {
    Node *n = malloc(sizeof *n);
    if (n == NULL) return -1;
    n->value = v;
    n->next = *head;
    *head = n;
    return 0;
}

static int push_back(Node **head, int v) {
    Node *n = malloc(sizeof *n);
    if (n == NULL) return -1;
    n->value = v;
    n->next = NULL;
    if (*head == NULL) { *head = n; return 0; }
    Node *cur = *head;
    while (cur->next != NULL) cur = cur->next;
    cur->next = n;
    return 0;
}

static int remove_value(Node **head, int v) {
    Node **pp = head;
    while (*pp != NULL) {
        if ((*pp)->value == v) {
            Node *victim = *pp;
            *pp = victim->next;
            free(victim);
            return 0;
        }
        pp = &(*pp)->next;
    }
    return -1;
}

static void print_list(const Node *head) {
    for (const Node *p = head; p != NULL; p = p->next) {
        printf("%d", p->value);
        if (p->next) printf(" -> ");
    }
    printf("\n");
}

static void free_list(Node *head) {
    while (head != NULL) {
        Node *next = head->next;
        free(head);
        head = next;
    }
}

int main(void) {
    Node *head = NULL;
    push_front(&head, 1);
    push_front(&head, 2);
    push_front(&head, 3);
    print_list(head);
    push_back(&head, 4);
    print_list(head);
    remove_value(&head, 2);
    print_list(head);
    free_list(head);
    return 0;
}
