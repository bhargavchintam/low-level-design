import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class Main {
    public static void main(String[] args) {
        User alice = new User("U1", "Alice");
        User bob = new User("U2", "Bob");
        User carol = new User("U3", "Carol");
        User dave = new User("U4", "Dave");

        Group trip = new Group("Goa Trip", List.of(alice, bob, carol, dave));
        Ledger ledger = new Ledger();

        // Alice pays 4000 for dinner, split equally among all 4
        Expense dinner = new Expense(alice, 4000.0, trip.getMembers(), new EqualSplit());
        ledger.addExpense(dinner);

        // Bob pays 3000 for a cab, exact amounts
        Expense cab = new Expense(bob, 3000.0, trip.getMembers(),
                new ExactSplit(Map.of(alice, 1000.0, bob, 500.0, carol, 1000.0, dave, 500.0)));
        ledger.addExpense(cab);

        // Carol pays 2000 for groceries, split by percentage
        Expense groceries = new Expense(carol, 2000.0, trip.getMembers(),
                new PercentSplit(Map.of(alice, 25.0, bob, 25.0, carol, 25.0, dave, 25.0)));
        ledger.addExpense(groceries);

        System.out.println("Group: " + trip.getName() + " | members: " + trip.getMembers());
        System.out.println("\nExpenses recorded:");
        for (Expense e : ledger.getExpenses()) {
            System.out.printf("  %s paid %.2f (%s)%n", e.getPayer(), e.getAmount(),
                    e.getSplitStrategy().getClass().getSimpleName());
        }

        System.out.println("\nNet balances:");
        ledger.printBalances();

        // demonstrate validation failure for a bad split
        System.out.println("\nAttempting an invalid ExactSplit (amounts don't sum to total):");
        try {
            new Expense(dave, 1000.0, trip.getMembers(),
                    new ExactSplit(Map.of(alice, 200.0, bob, 200.0, carol, 200.0, dave, 200.0)));
        } catch (IllegalArgumentException e) {
            System.out.println("  rejected as expected: " + e.getMessage());
        }
    }
}

class User {
    private final String id;
    private final String name;

    User(String id, String name) {
        this.id = id;
        this.name = name;
    }

    String getId() {
        return id;
    }

    @Override
    public String toString() {
        return name;
    }
}

class Group {
    private final String name;
    private final List<User> members;

    Group(String name, List<User> members) {
        this.name = name;
        this.members = members;
    }

    String getName() {
        return name;
    }

    List<User> getMembers() {
        return members;
    }
}

interface SplitStrategy {
    /** Computes each participant's owed share; shares must sum to totalAmount. */
    Map<User, Double> computeShares(double totalAmount, List<User> participants);
}

class EqualSplit implements SplitStrategy {
    @Override
    public Map<User, Double> computeShares(double totalAmount, List<User> participants) {
        Map<User, Double> shares = new LinkedHashMap<>();
        double each = totalAmount / participants.size();
        for (User u : participants) {
            shares.put(u, each);
        }
        return shares;
    }
}

class ExactSplit implements SplitStrategy {
    private final Map<User, Double> amounts;

    ExactSplit(Map<User, Double> amounts) {
        this.amounts = amounts;
    }

    @Override
    public Map<User, Double> computeShares(double totalAmount, List<User> participants) {
        double sum = amounts.values().stream().mapToDouble(Double::doubleValue).sum();
        if (Math.abs(sum - totalAmount) > 0.01) {
            throw new IllegalArgumentException(
                    "exact amounts (" + sum + ") do not sum to total (" + totalAmount + ")");
        }
        return new LinkedHashMap<>(amounts);
    }
}

class PercentSplit implements SplitStrategy {
    private final Map<User, Double> percentages;

    PercentSplit(Map<User, Double> percentages) {
        this.percentages = percentages;
    }

    @Override
    public Map<User, Double> computeShares(double totalAmount, List<User> participants) {
        double sum = percentages.values().stream().mapToDouble(Double::doubleValue).sum();
        if (Math.abs(sum - 100.0) > 0.01) {
            throw new IllegalArgumentException("percentages (" + sum + ") do not sum to 100");
        }
        Map<User, Double> shares = new LinkedHashMap<>();
        for (Map.Entry<User, Double> entry : percentages.entrySet()) {
            shares.put(entry.getKey(), totalAmount * entry.getValue() / 100.0);
        }
        return shares;
    }
}

class Expense {
    private final User payer;
    private final double amount;
    private final SplitStrategy splitStrategy;
    private final Map<User, Double> shares;

    Expense(User payer, double amount, List<User> participants, SplitStrategy splitStrategy) {
        this.payer = payer;
        this.amount = amount;
        this.splitStrategy = splitStrategy;
        this.shares = splitStrategy.computeShares(amount, participants);
    }

    User getPayer() {
        return payer;
    }

    double getAmount() {
        return amount;
    }

    SplitStrategy getSplitStrategy() {
        return splitStrategy;
    }

    Map<User, Double> getShares() {
        return shares;
    }
}

/** Nets out who-owes-whom across every recorded expense. */
class Ledger {
    private final List<Expense> expenses = new ArrayList<>();
    // balances.get(a).get(b) = how much `a` owes `b` (net, can be negative)
    private final Map<User, Map<User, Double>> balances = new LinkedHashMap<>();

    void addExpense(Expense expense) {
        expenses.add(expense);
        User payer = expense.getPayer();
        for (Map.Entry<User, Double> entry : expense.getShares().entrySet()) {
            User debtor = entry.getKey();
            double share = entry.getValue();
            if (debtor == payer) {
                continue;
            }
            adjust(debtor, payer, share);
        }
    }

    private void adjust(User debtor, User creditor, double amount) {
        balances.computeIfAbsent(debtor, k -> new LinkedHashMap<>())
                .merge(creditor, amount, Double::sum);
        balances.computeIfAbsent(creditor, k -> new LinkedHashMap<>())
                .merge(debtor, -amount, Double::sum);
    }

    List<Expense> getExpenses() {
        return expenses;
    }

    void printBalances() {
        boolean anyDebt = false;
        for (Map.Entry<User, Map<User, Double>> entry : balances.entrySet()) {
            User debtor = entry.getKey();
            for (Map.Entry<User, Double> owed : entry.getValue().entrySet()) {
                double amount = owed.getValue();
                if (amount > 0.01) {
                    System.out.printf("  %s owes %s: %.2f%n", debtor, owed.getKey(), amount);
                    anyDebt = true;
                }
            }
        }
        if (!anyDebt) {
            System.out.println("  all settled up");
        }
    }
}
