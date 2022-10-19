from brownie import network, reverts
from scripts.helper import LOCAL_BLOCKCHAIN_ENV, get_account
from scripts.deploy import deploy_cube_token
from web3 import Web3
import pytest


def test_cannot_mint_if_non_owner():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    non_owner = get_account(index=1)
    cube_token = deploy_cube_token()
    # Act / Assert
    expected_revert_string = (
        "typed error: "
        + Web3.keccak(text="CubeToken__SenderIsNotTheMinter()")[:4].hex()
    )
    with reverts(expected_revert_string):
        cube_token.mint(non_owner.address, 1, {"from": non_owner})


def test_can_mint_if_owner(amount_to_stake):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token = deploy_cube_token()
    # Transfer the role to owner
    minter_role = cube_token.MINTER_ROLE()
    grantTx = cube_token.grantRole(minter_role, account.address, {"from": account})
    grantTx.wait(1)
    # Act
    mintTx = cube_token.mint(account.address, amount_to_stake, {"from": account})
    mintTx.wait(1)
    # Assert
    assert cube_token.totalSupply() == amount_to_stake
