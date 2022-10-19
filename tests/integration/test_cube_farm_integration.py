from brownie import network
from scripts.helper import (
    LOCAL_BLOCKCHAIN_ENV,
    DECIMALS,
    get_account,
    get_contract,
    calculate_rewards_based_on_time,
)
from scripts.get_weth import get_weth
from scripts.deploy import deploy
import pytest
import time
import math

# Tested with weth token
# Make sure to have eth token in your tesnet account
def test_can_stake_tokens_unstake_and_claim_rewards(amount_to_stake):
    # Arrange
    if network.show_active() in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for integration testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    get_weth(account=account, amount=amount_to_stake)
    weth_token = get_contract("weth_token")
    weth_price_feed = get_contract("eth_usd_price_feed")
    # Transfer the role to cube_farm
    minter_role = cube_token.MINTER_ROLE()
    grant_role_tx = cube_token.grantRole(
        minter_role, cube_farm.address, {"from": account}
    )
    grant_role_tx.wait(1)
    set_price_feed_tx = cube_farm.setPriceFeedContract(
        weth_token.address,
        weth_price_feed,
        {"from": account},
    )
    set_price_feed_tx.wait(1)
    add_allowed_token_tx = cube_farm.addAllowedToken(
        weth_token.address, {"from": account}
    )
    add_allowed_token_tx.wait(1)
    approve_tx = weth_token.approve(
        cube_farm.address, amount_to_stake, {"from": account}
    )
    approve_tx.wait(1)
    # Act
    stake_token_tx = cube_farm.stakeTokens(
        amount_to_stake, weth_token.address, {"from": account}
    )
    stake_token_tx.wait(1)
    start_time_when_staked = cube_farm.getUserTokenStartTime(
        account.address, weth_token.address
    )
    time.sleep(10)
    (_, price, _, _, _) = weth_price_feed.latestRoundData()
    decimals = weth_price_feed.decimals()
    claim_yield_rewards_tx = cube_farm.claimYieldRewards({"from": account})
    claim_yield_rewards_tx.wait(1)
    start_time_when_claimed = cube_farm.getUserTokenStartTime(
        account.address, weth_token.address
    )
    unstake_token_tx = cube_farm.unstakeTokens(
        amount_to_stake, weth_token.address, {"from": account}
    )
    unstake_token_tx.wait(1)
    expected_rewards = calculate_rewards_based_on_time(
        amount_to_stake,
        price,
        start_time_when_staked,
        start_time_when_claimed,
        decimals=decimals,
    ) / (10**DECIMALS)
    cube_balance = cube_token.balanceOf(account) / (10**DECIMALS)
    # Assert
    # Removing the decimals and asserting with isclose because the price probably moving a bit between
    # latestRoundData from the contract and the one I call
    assert cube_balance > 0
    assert math.isclose(cube_balance, expected_rewards, rel_tol=1e-4)
    assert cube_farm.getUserTokenBalance(account.address, weth_token.address) == 0
    assert cube_farm.getNumberOfTokenStaked(account.address) == 0
    assert account.address not in cube_farm.getStakers()
    assert len(stake_token_tx.events["TokenStaked"]) == 1
    assert len(claim_yield_rewards_tx.events["YieldRewarded"]) == 1
    assert len(unstake_token_tx.events["TokenUnstaked"]) == 1
