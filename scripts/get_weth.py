from brownie import interface, config, network
from scripts.helper import get_account
from web3 import Web3

AMOUNT = Web3.toWei(0.1, "ether")


def main():
    get_weth()


def get_weth(account=get_account(), amount=AMOUNT):
    weth_token = interface.IWeth(
        config["networks"][network.show_active()]["weth_token"]
    )
    deposit_tx = weth_token.deposit({"value": amount, "from": account})
    deposit_tx.wait(1)
