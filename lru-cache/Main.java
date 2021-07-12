import java.util.HashMap;
import java.util.Map;

public class Main {
    public static void main(String[] args) {
        LRUCache<Integer, String> cache = new LRUCache<>(3);

        System.out.println("put(1, A)");
        cache.put(1, "A");
        cache.printContents();

        System.out.println("put(2, B)");
        cache.put(2, "B");
        cache.printContents();

        System.out.println("put(3, C)");
        cache.put(3, "C");
        cache.printContents();

        System.out.println("get(1) -> " + cache.get(1) + "   (1 becomes most recent)");
        cache.printContents();

        System.out.println("put(4, D)  (cache full, evicts least recently used)");
        cache.put(4, "D");
        cache.printContents();

        System.out.println("get(2) -> " + cache.get(2) + "   (evicted earlier, expect null)");
        cache.printContents();

        System.out.println("put(5, E)  (evicts least recently used again)");
        cache.put(5, "E");
        cache.printContents();
    }
}

class LRUCache<K, V> {
    private static class Node<K, V> {
        K key;
        V value;
        Node<K, V> prev;
        Node<K, V> next;

        Node(K key, V value) {
            this.key = key;
            this.value = value;
        }
    }

    private final int capacity;
    private final Map<K, Node<K, V>> lookup = new HashMap<>();
    // sentinel head/tail so insert/remove never has to special-case list ends
    private final Node<K, V> head = new Node<>(null, null);
    private final Node<K, V> tail = new Node<>(null, null);

    LRUCache(int capacity) {
        if (capacity <= 0) {
            throw new IllegalArgumentException("capacity must be positive");
        }
        this.capacity = capacity;
        head.next = tail;
        tail.prev = head;
    }

    V get(K key) {
        Node<K, V> node = lookup.get(key);
        if (node == null) {
            return null;
        }
        moveToFront(node);
        return node.value;
    }

    void put(K key, V value) {
        Node<K, V> existing = lookup.get(key);
        if (existing != null) {
            existing.value = value;
            moveToFront(existing);
            return;
        }

        if (lookup.size() == capacity) {
            Node<K, V> lru = tail.prev;
            remove(lru);
            lookup.remove(lru.key);
        }

        Node<K, V> node = new Node<>(key, value);
        lookup.put(key, node);
        insertAtFront(node);
    }

    private void moveToFront(Node<K, V> node) {
        remove(node);
        insertAtFront(node);
    }

    private void remove(Node<K, V> node) {
        node.prev.next = node.next;
        node.next.prev = node.prev;
    }

    private void insertAtFront(Node<K, V> node) {
        node.next = head.next;
        node.prev = head;
        head.next.prev = node;
        head.next = node;
    }

    void printContents() {
        StringBuilder sb = new StringBuilder("  [most recent -> least recent] ");
        Node<K, V> current = head.next;
        while (current != tail) {
            sb.append(current.key).append("=").append(current.value);
            if (current.next != tail) {
                sb.append(", ");
            }
            current = current.next;
        }
        System.out.println(sb);
    }
}
