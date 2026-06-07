from bank_accounts import *

sjtroxel = BankAccount(1000, "sjtroxel")
Sara = BankAccount(2000, "Sara")

sjtroxel.getBalance()
Sara.getBalance()

Sara.deposit(500)

sjtroxel.withdraw(10000)
sjtroxel.withdraw(10)

sjtroxel.transfer(10000, Sara)
sjtroxel.transfer(100, Sara)

Jim = InterestRewardsAcct(1000, "Jim")

Jim.getBalance()

Jim.deposit(100)

Jim.transfer(100, sjtroxel)

Blaze = SavingsAcct(1000, "Blaze")

Blaze.getBalance()

Blaze.deposit(100)

Blaze.transfer(10000, Sara)
Blaze.transfer(1000, Sara)