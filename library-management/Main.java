import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class Main {
    public static void main(String[] args) {
        Library library = new Library();

        Book book = new Book("978-0-13-468599-1", "Effective Java", "Joshua Bloch");
        book.addCopy(new BookItem("COPY-1"));
        library.addBook(book);

        Member alice = new Member("M1", "Alice");
        Member bob = new Member("M2", "Bob");
        library.registerMember(alice);
        library.registerMember(bob);

        System.out.println("-- Alice checks out the only copy --");
        BookItem loanedToAlice = library.checkout(alice, book.getIsbn());
        System.out.println(loanedToAlice != null
                ? "Alice checked out " + loanedToAlice.getBarcode()
                : "Checkout failed for Alice");

        System.out.println("\n-- Bob tries to check out the same title --");
        BookItem loanedToBob = library.checkout(bob, book.getIsbn());
        if (loanedToBob == null) {
            System.out.println("No copies available, Bob subscribes for a return notification");
            library.subscribeForAvailability(bob, book.getIsbn());
        }

        System.out.println("\n-- Alice returns her copy --");
        library.returnBook(loanedToAlice);
    }
}

enum BookStatus {
    AVAILABLE,
    LOANED,
    RESERVED
}

interface BookAvailabilityObserver {
    void onAvailable(Book book);
}

class BookItem {
    private final String barcode;
    private BookStatus status;

    BookItem(String barcode) {
        this.barcode = barcode;
        this.status = BookStatus.AVAILABLE;
    }

    String getBarcode() {
        return barcode;
    }

    BookStatus getStatus() {
        return status;
    }

    void setStatus(BookStatus status) {
        this.status = status;
    }
}

class Book {
    private final String isbn;
    private final String title;
    private final String author;
    private final List<BookItem> copies = new ArrayList<>();
    // members waiting on the next returned copy - classic Observer pattern
    private final List<BookAvailabilityObserver> subscribers = new ArrayList<>();

    Book(String isbn, String title, String author) {
        this.isbn = isbn;
        this.title = title;
        this.author = author;
    }

    String getIsbn() {
        return isbn;
    }

    String getTitle() {
        return title;
    }

    void addCopy(BookItem item) {
        copies.add(item);
    }

    List<BookItem> getCopies() {
        return copies;
    }

    void subscribe(BookAvailabilityObserver observer) {
        subscribers.add(observer);
    }

    void notifySubscribers() {
        // one-shot notification: once told, a member falls off the list
        for (BookAvailabilityObserver observer : subscribers) {
            observer.onAvailable(this);
        }
        subscribers.clear();
    }
}

class Member implements BookAvailabilityObserver {
    private final String id;
    private final String name;

    Member(String id, String name) {
        this.id = id;
        this.name = name;
    }

    String getId() {
        return id;
    }

    String getName() {
        return name;
    }

    @Override
    public void onAvailable(Book book) {
        System.out.println(name + " notified: \"" + book.getTitle() + "\" is available again.");
    }
}

class Library {
    private final Map<String, Book> catalog = new HashMap<>();
    private final Map<String, Member> members = new HashMap<>();

    void addBook(Book book) {
        catalog.put(book.getIsbn(), book);
    }

    void registerMember(Member member) {
        members.put(member.getId(), member);
    }

    BookItem checkout(Member member, String isbn) {
        Book book = catalog.get(isbn);
        if (book == null) {
            return null;
        }
        for (BookItem item : book.getCopies()) {
            if (item.getStatus() == BookStatus.AVAILABLE) {
                item.setStatus(BookStatus.LOANED);
                return item;
            }
        }
        return null;
    }

    void returnBook(BookItem item) {
        item.setStatus(BookStatus.AVAILABLE);
        for (Book book : catalog.values()) {
            if (book.getCopies().contains(item)) {
                System.out.println("Copy " + item.getBarcode() + " returned to catalog");
                book.notifySubscribers();
                return;
            }
        }
    }

    void subscribeForAvailability(Member member, String isbn) {
        Book book = catalog.get(isbn);
        if (book != null) {
            book.subscribe(member);
        }
    }
}
