import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class Main {
    public static void main(String[] args) {
        Logger chain = new ConsoleLogger(Level.DEBUG,
                new FileLogger(Level.INFO,
                        new AlertLogger(Level.ERROR, null)));

        System.out.println("Chain: ConsoleLogger(DEBUG) -> FileLogger(INFO) -> AlertLogger(ERROR)\n");

        chain.log(Level.DEBUG, "connection pool acquired a new connection");
        chain.log(Level.INFO, "user 42 logged in");
        chain.log(Level.ERROR, "payment gateway timed out after 3 retries");
        chain.log(Level.INFO, "cache warmed for region us-east-1");
        chain.log(Level.DEBUG, "cache lookup miss for key session:42");
    }
}

enum Level {
    DEBUG(0), INFO(1), ERROR(2);

    final int severity;

    Level(int severity) {
        this.severity = severity;
    }
}

abstract class Logger {
    private final Level level;
    private final Logger next;

    Logger(Level level, Logger next) {
        this.level = level;
        this.next = next;
    }

    // every handler at or above this message's severity gets a chance to handle it
    final void log(Level messageLevel, String message) {
        if (messageLevel.severity >= level.severity) {
            write(messageLevel, message);
        }
        if (next != null) {
            next.log(messageLevel, message);
        }
    }

    abstract void write(Level messageLevel, String message);

    static String timestamp() {
        return LocalDateTime.now().format(DateTimeFormatter.ofPattern("HH:mm:ss"));
    }
}

class ConsoleLogger extends Logger {
    ConsoleLogger(Level level, Logger next) {
        super(level, next);
    }

    @Override
    void write(Level messageLevel, String message) {
        System.out.printf("[CONSOLE][%s][%s] %s%n", timestamp(), messageLevel, message);
    }
}

class FileLogger extends Logger {
    // simulated: prints with a [FILE] prefix instead of touching disk, to keep the demo self-contained
    FileLogger(Level level, Logger next) {
        super(level, next);
    }

    @Override
    void write(Level messageLevel, String message) {
        System.out.printf("[FILE][%s][%s] %s%n", timestamp(), messageLevel, message);
    }
}

class AlertLogger extends Logger {
    AlertLogger(Level level, Logger next) {
        super(level, next);
    }

    @Override
    void write(Level messageLevel, String message) {
        System.out.printf("[ALERT][%s][%s] paging on-call: %s%n", timestamp(), messageLevel, message);
    }
}
