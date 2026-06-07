"""
Tests for bank_accounts.py  (Lesson 20 OOP project)

WHAT THIS FILE IS
-----------------
This is a pytest test suite. Each `test_...` function below is one small,
independent experiment: it builds an account, does ONE thing to it, and then
asserts ("claims") what the result should be. If reality matches the claim,
the test passes (green). If not, pytest fails it (red) and shows you exactly
which line and what the actual vs expected values were.

NAMING CONVENTION (this is not optional — it's how pytest finds tests):
  - the file must be named  test_*.py  or  *_test.py
  - each test function must start with  test_
pytest auto-discovers anything matching those patterns. No "main", no manual
list of tests to run. You just point pytest at the folder.

HOW TO RUN IT (from the repo root /home/sjtroxel/python-tutorial-course):
    ./venv/bin/python -m pytest Lesson20/ -v
Or from inside the Lesson20 folder:
    ../venv/bin/python -m pytest -v
The -v ("verbose") flag lists each test by name with PASS/FAIL.

THE CORE PATTERN: every test is "Arrange, Act, Assert"
  Arrange -> set up the objects you need
  Act     -> call the one method you're testing
  Assert  -> state what must be true afterward (the `assert` keyword)
"""

import pytest

# Import the classes under test from the sibling file. Because this test file
# lives in the same folder as bank_accounts.py, pytest puts that folder on the
# import path, so a plain `from bank_accounts import ...` works.
from bank_accounts import (
    BankAccount,
    InterestRewardsAcct,
    SavingsAcct,
    BalanceException,
)


# ---------------------------------------------------------------------------
# BankAccount — the base class
# ---------------------------------------------------------------------------

def test_bank_account_init_sets_balance_and_name():
    # Arrange + Act: just constructing the object IS the thing we're testing
    acct = BankAccount(100, "Test")
    # Assert: the constructor should have stored both values on the instance
    assert acct.balance == 100
    assert acct.name == "Test"


def test_plain_deposit_adds_the_full_amount():
    acct = BankAccount(100, "Test")
    acct.deposit(100)
    # A *plain* BankAccount has NO interest, so 100 + 100 = 200 exactly.
    assert acct.balance == 200


def test_withdraw_reduces_balance_when_funds_available():
    acct = BankAccount(100, "Test")
    acct.withdraw(40)
    assert acct.balance == 60


def test_viable_transaction_raises_when_funds_insufficient():
    # viableTransaction() is the *guard*. It RAISES BalanceException directly
    # (it does not catch anything), so we can test the raise itself.
    #
    # `with pytest.raises(...)` means: "I EXPECT this block to throw this error.
    # Pass the test if it does, fail if it doesn't." It's the standard way to
    # test that error paths actually fire.
    acct = BankAccount(100, "Test")
    with pytest.raises(BalanceException):
        acct.viableTransaction(500)   # asking for more than the balance


def test_withdraw_with_insufficient_funds_leaves_balance_unchanged():
    # IMPORTANT subtlety: withdraw() calls viableTransaction() inside a try/except
    # and SWALLOWS the BalanceException (it just prints a message). So from the
    # outside, no error escapes -- which means we CANNOT use pytest.raises here.
    # Instead we test the observable effect: the balance must be untouched.
    acct = BankAccount(100, "Test")
    acct.withdraw(500)            # over-withdraw: caught internally, no crash
    assert acct.balance == 100    # nothing was deducted


def test_transfer_moves_funds_between_two_accounts():
    sender = BankAccount(100, "Sender")
    receiver = BankAccount(50, "Receiver")
    sender.transfer(30, receiver)
    assert sender.balance == 70    # 100 - 30
    assert receiver.balance == 80  # 50 + 30 (receiver is plain: no interest)


def test_transfer_with_insufficient_funds_leaves_both_unchanged():
    # transfer() also catches BalanceException internally. If the sender can't
    # cover it, the guard fires BEFORE any money moves, so both stay put.
    sender = BankAccount(100, "Sender")
    receiver = BankAccount(50, "Receiver")
    sender.transfer(500, receiver)
    assert sender.balance == 100
    assert receiver.balance == 50


# ---------------------------------------------------------------------------
# InterestRewardsAcct — overrides deposit() to add 5%
# ---------------------------------------------------------------------------

def test_interest_account_deposit_adds_5_percent():
    acct = InterestRewardsAcct(100, "Rewards")
    acct.deposit(100)
    # 100 + (100 * 1.05) = 205.0
    #
    # NOTE: we compare with pytest.approx, NOT ==. Floating-point math is not
    # exact in binary. This particular case happens to land on a clean 205.0,
    # but the moment you deposit a "messy" amount it won't (see next test).
    # Using approx everywhere for float math is the safe habit.
    assert acct.balance == pytest.approx(205.0)


def test_interest_deposit_needs_approx_for_messy_floats():
    acct = InterestRewardsAcct(100, "Rewards")
    acct.deposit(19.99)
    # The "true" math is 100 + (19.99 * 1.05) = 120.9895
    # but in float it's actually 120.98949999999999.
    # `== 120.9895` would FAIL. pytest.approx absorbs that tiny rounding error.
    assert acct.balance == pytest.approx(120.9895)


def test_interest_account_inherits_plain_withdraw():
    # InterestRewardsAcct only overrides deposit(). It does NOT touch withdraw,
    # so it inherits BankAccount's fee-free withdraw straight through.
    acct = InterestRewardsAcct(100, "Rewards")
    acct.withdraw(40)
    assert acct.balance == 60   # no fee, plain subtraction


# ---------------------------------------------------------------------------
# SavingsAcct — child of InterestRewardsAcct; adds a $5 withdrawal fee
# ---------------------------------------------------------------------------

def test_savings_account_init_sets_fee():
    acct = SavingsAcct(100, "Savings")
    # SavingsAcct overrides __init__ to add self.fee, but calls super().__init__
    # first, so balance/name are still set by the grandparent BankAccount.
    assert acct.fee == 5
    assert acct.balance == 100
    assert acct.name == "Savings"


def test_savings_withdraw_subtracts_amount_plus_fee():
    acct = SavingsAcct(100, "Savings")
    acct.withdraw(20)
    # SavingsAcct overrides withdraw to charge the fee: 100 - (20 + 5) = 75
    assert acct.balance == 75


def test_savings_withdraw_blocked_when_fee_pushes_over_balance():
    # The fee is part of the affordability check. Asking for the whole balance
    # fails because amount + fee (100 + 5 = 105) exceeds 100. The exception is
    # caught inside withdraw, so the balance is simply left unchanged.
    acct = SavingsAcct(100, "Savings")
    acct.withdraw(100)
    assert acct.balance == 100


def test_savings_account_inherits_interest_deposit():
    # This is the exact thing you spotted by reading the code:
    # SavingsAcct(InterestRewardsAcct) defines NO deposit of its own, so Python's
    # method resolution walks UP the chain and finds InterestRewardsAcct.deposit
    # (the +5% one) before it ever reaches BankAccount's plain deposit.
    # This test PINS that behavior: if someone later changed the inheritance so
    # savings deposits stopped earning interest, this test would go red and tell
    # them. That's what tests are for -- they freeze intended behavior in place.
    acct = SavingsAcct(100, "Savings")
    acct.deposit(100)
    assert acct.balance == pytest.approx(205.0)   # +5%, inherited
