from brownie import network, exceptions, chain, reverts
from scripts.helper import (
    LOCAL_BLOCKCHAIN_ENV,
    RATE,
    INITIAL_PRICE_FEED_VALUE,
    DECIMALS,
    get_account,
    get_contract,
    calculate_rewards_based_on_time,
)
from scripts.deploy import deploy
from web3 import Web3
import pytest
import math

# Precision should be enough
REL_TOL = 1e-6


def test_constructor_set_up_correctly():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    cube_token, cube_farm = deploy()
    # Act / Assert
    assert cube_farm.getRate() == RATE
    assert cube_token.address == cube_farm.getCubeTokenAddress()


def test_cannot_set_price_feed_if_non_owner():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    non_owner = get_account(index=1)
    cube_token, cube_farm = deploy()
    # Act / Assert
    with pytest.raises(exceptions.VirtualMachineError):
        cube_farm.setPriceFeedContract(
            cube_token.address,
            get_contract("dai_usd_price_feed"),
            {"from": non_owner},
        )


def test_can_set_price_feed_if_owner():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Act
    set_price_feed_tx = cube_farm.setPriceFeedContract(
        cube_token.address,
        get_contract("dai_usd_price_feed"),
        {"from": account},
    )
    set_price_feed_tx.wait(1)
    # Assert
    assert cube_farm.getPriceFeedContract(cube_token.address) == get_contract(
        "dai_usd_price_feed"
    )


def test_cannot_add_allowed_token_if_non_owner():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    non_owner = get_account(index=1)
    cube_token, cube_farm = deploy()
    # Act / Assert
    with pytest.raises(exceptions.VirtualMachineError):
        cube_farm.addAllowedToken(get_contract("weth_token"), {"from": non_owner})


def test_can_add_allowed_token_if_owner():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Act
    add_allowed_token_tx = cube_farm.addAllowedToken(
        get_contract("weth_token"), {"from": account}
    )
    add_allowed_token_tx.wait(1)
    # Assert
    assert get_contract("weth_token") in cube_farm.getAllowedTokens()


def test_cannot_stake_token_if_amount_zero():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Act / Assert
    expected_revert_string = (
        "typed error: "
        + Web3.keccak(text="CubeFarm__CannotStakeAmountZero()")[:4].hex()
    )
    with reverts(expected_revert_string):
        cube_farm.stakeTokens(0, cube_token.address, {"from": account})


def test_cannot_stake_token_if_user_balance_zero(amount_to_stake):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Act / Assert
    expected_revert_string = (
        "typed error: "
        + Web3.keccak(text="CubeFarm__CannotStakeAmountZero()")[:4].hex()
    )
    with reverts(expected_revert_string):
        cube_farm.stakeTokens(amount_to_stake, cube_token.address, {"from": account})


def test_cannot_stake_token_if_token_not_allowed(amount_to_stake):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Transfer the role to CubeFarm
    minter_role = cube_token.MINTER_ROLE()
    grant_role_tx = cube_token.grantRole(
        minter_role, cube_farm.address, {"from": account}
    )
    grant_role_tx.wait(1)
    mint_tx = cube_token.mint(account.address, amount_to_stake, {"from": cube_farm})
    mint_tx.wait(1)
    # Act / Assert
    expected_revert_string = (
        "typed error: " + Web3.keccak(text="CubeFarm__TokenNotAllowed()")[:4].hex()
    )
    with reverts(expected_revert_string):
        cube_farm.stakeTokens(amount_to_stake, cube_token.address, {"from": account})


def test_can_stake_token(amount_to_stake):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Transfer the role to CubeFarm
    minter_role = cube_token.MINTER_ROLE()
    grant_role_tx = cube_token.grantRole(
        minter_role, cube_farm.address, {"from": account}
    )
    grant_role_tx.wait(1)
    mint_tx = cube_token.mint(account.address, amount_to_stake, {"from": cube_farm})
    mint_tx.wait(1)
    set_price_feed_tx = cube_farm.setPriceFeedContract(
        cube_token.address,
        get_contract("dai_usd_price_feed"),
        {"from": account},
    )
    set_price_feed_tx.wait(1)
    add_allowed_token_tx = cube_farm.addAllowedToken(
        cube_token.address, {"from": account}
    )
    add_allowed_token_tx.wait(1)
    approve_tx = cube_token.approve(
        cube_farm.address, amount_to_stake, {"from": account}
    )
    approve_tx.wait(1)
    # Act
    stake_token_tx = cube_farm.stakeTokens(
        amount_to_stake, cube_token.address, {"from": account}
    )
    stake_token_tx.wait(1)
    # Assert
    assert cube_token.balanceOf(account) == 0
    assert (
        cube_farm.getUserTokenBalance(account.address, cube_token.address)
        == amount_to_stake
    )
    assert cube_farm.getNumberOfTokenStaked(account.address) == 1
    assert account.address in cube_farm.getStakers()
    assert len(stake_token_tx.events["TokenStaked"]) == 1


def test_cannot_unstake_token_if_user_balance_zero(amount_to_stake):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Act / Assert
    expected_revert_string = (
        "typed error: "
        + Web3.keccak(text="CubeFarm__CannotUnStakeZeroBalance()")[:4].hex()
    )
    with reverts(expected_revert_string):
        cube_farm.unstakeTokens(amount_to_stake, cube_token.address, {"from": account})


def test_cannot_unstake_token_if_amount_greater_than_user_balance(amount_to_stake):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Transfer the role to CubeFarm
    minter_role = cube_token.MINTER_ROLE()
    grant_role_tx = cube_token.grantRole(
        minter_role, cube_farm.address, {"from": account}
    )
    grant_role_tx.wait(1)
    mint_tx = cube_token.mint(account.address, amount_to_stake, {"from": cube_farm})
    mint_tx.wait(1)
    add_allowed_token_tx = cube_farm.addAllowedToken(
        cube_token.address, {"from": account}
    )
    add_allowed_token_tx.wait(1)
    approve_tx = cube_token.approve(
        cube_farm.address, amount_to_stake, {"from": account}
    )
    approve_tx.wait(1)
    stake_token_tx = cube_farm.stakeTokens(
        amount_to_stake, cube_token.address, {"from": account}
    )
    stake_token_tx.wait(1)
    # Act / Assert
    expected_revert_string = (
        "typed error: "
        + Web3.keccak(text="CubeFarm__CannotUnStakeMoreThanUserBalance()")[:4].hex()
    )
    with reverts(expected_revert_string):
        cube_farm.unstakeTokens(
            amount_to_stake + 1, cube_token.address, {"from": account}
        )


def test_can_unstake_token(amount_to_stake):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Transfer the role to CubeFarm
    minter_role = cube_token.MINTER_ROLE()
    grant_role_tx = cube_token.grantRole(
        minter_role, cube_farm.address, {"from": account}
    )
    grant_role_tx.wait(1)
    mint_tx = cube_token.mint(account.address, amount_to_stake, {"from": cube_farm})
    mint_tx.wait(1)
    set_price_feed_tx = cube_farm.setPriceFeedContract(
        cube_token.address,
        get_contract("dai_usd_price_feed"),
        {"from": account},
    )
    set_price_feed_tx.wait(1)
    add_allowed_token_tx = cube_farm.addAllowedToken(
        cube_token.address, {"from": account}
    )
    add_allowed_token_tx.wait(1)
    approve_tx = cube_token.approve(
        cube_farm.address, amount_to_stake, {"from": account}
    )
    approve_tx.wait(1)
    stake_token_tx = cube_farm.stakeTokens(
        amount_to_stake, cube_token.address, {"from": account}
    )
    stake_token_tx.wait(1)
    # Act
    unstake_token_tx = cube_farm.unstakeTokens(
        amount_to_stake, cube_token.address, {"from": account}
    )
    unstake_token_tx.wait(1)
    # Assert
    assert cube_token.balanceOf(account) == amount_to_stake
    assert cube_farm.getUserTokenBalance(account.address, cube_token.address) == 0
    assert cube_farm.getNumberOfTokenStaked(account.address) == 0
    assert account.address not in cube_farm.getStakers()
    assert len(unstake_token_tx.events["TokenUnstaked"]) == 1


def test_can_get_total_pending_rewards_when_zero_token_staked():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Act / Assert
    assert cube_farm.getTotalPendingRewards(account.address) == 0


def test_can_get_total_pending_rewards(amount_to_stake):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Transfer the role to CubeFarm
    minter_role = cube_token.MINTER_ROLE()
    grant_role_tx = cube_token.grantRole(
        minter_role, cube_farm.address, {"from": account}
    )
    grant_role_tx.wait(1)
    mint_tx = cube_token.mint(account.address, amount_to_stake, {"from": cube_farm})
    mint_tx.wait(1)
    set_price_feed_tx = cube_farm.setPriceFeedContract(
        cube_token.address,
        get_contract("dai_usd_price_feed"),
        {"from": account},
    )
    set_price_feed_tx.wait(1)
    add_allowed_token_tx = cube_farm.addAllowedToken(
        cube_token.address, {"from": account}
    )
    add_allowed_token_tx.wait(1)
    approve_tx = cube_token.approve(
        cube_farm.address, amount_to_stake, {"from": account}
    )
    approve_tx.wait(1)
    stake_token_tx = cube_farm.stakeTokens(
        amount_to_stake, cube_token.address, {"from": account}
    )
    stake_token_tx.wait(1)
    time_after_staking = chain.time()
    # Mine 1 block and add rate time
    chain.mine(1, chain.sleep(RATE))
    time_after_one_day_staking = chain.time()
    expected_pending_rewards = calculate_rewards_based_on_time(
        amount_to_stake,
        INITIAL_PRICE_FEED_VALUE,
        time_after_staking,
        time_after_one_day_staking,
    )
    # Act
    total_pending_rewards = cube_farm.getTotalPendingRewards(account.address)
    # Assert
    assert total_pending_rewards > 0
    assert total_pending_rewards >= expected_pending_rewards


def test_cannot_claim_yield_rewards_if_no_rewards():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Act / Assert
    expected_revert_string = (
        "typed error: " + Web3.keccak(text="CubeFarm__NoRewardsToTransfer()")[:4].hex()
    )
    with reverts(expected_revert_string):
        cube_farm.claimYieldRewards({"from": account})


def test_can_claim_yield_rewards(amount_to_stake):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Transfer the role to CubeFarm
    minter_role = cube_token.MINTER_ROLE()
    grant_role_tx = cube_token.grantRole(
        minter_role, cube_farm.address, {"from": account}
    )
    grant_role_tx.wait(1)
    mint_tx = cube_token.mint(account.address, amount_to_stake, {"from": cube_farm})
    mint_tx.wait(1)
    set_price_feed_tx = cube_farm.setPriceFeedContract(
        cube_token.address,
        get_contract("dai_usd_price_feed"),
        {"from": account},
    )
    set_price_feed_tx.wait(1)
    add_allowed_token_tx = cube_farm.addAllowedToken(
        cube_token.address, {"from": account}
    )
    add_allowed_token_tx.wait(1)
    approve_tx = cube_token.approve(
        cube_farm.address, amount_to_stake, {"from": account}
    )
    approve_tx.wait(1)
    stake_token_tx = cube_farm.stakeTokens(
        amount_to_stake, cube_token.address, {"from": account}
    )
    stake_token_tx.wait(1)
    start_time_when_staked = cube_farm.getUserTokenStartTime(
        account.address, cube_token.address
    )
    # Add rate time (block is mined on the next transaction)
    chain.sleep(RATE)
    # Act
    claim_yield_rewards_tx = cube_farm.claimYieldRewards({"from": account})
    claim_yield_rewards_tx.wait(1)
    start_time_when_claimed = cube_farm.getUserTokenStartTime(
        account.address, cube_token.address
    )
    expected_rewards = calculate_rewards_based_on_time(
        amount_to_stake,
        INITIAL_PRICE_FEED_VALUE,
        start_time_when_staked,
        start_time_when_claimed,
    ) / (10**DECIMALS)
    cube_balance = cube_token.balanceOf(account) / (10**DECIMALS)
    # Assert
    # Removing the decimals and asserting with isclose because python and solidity round and can be a bit different
    assert cube_balance > 0
    assert math.isclose(cube_balance, expected_rewards, rel_tol=REL_TOL)
    assert len(claim_yield_rewards_tx.events["YieldRewarded"]) == 1


def test_can_claim_yield_rewards_after_unstake(amount_to_stake):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Transfer the role to CubeFarm
    minter_role = cube_token.MINTER_ROLE()
    grant_role_tx = cube_token.grantRole(
        minter_role, cube_farm.address, {"from": account}
    )
    grant_role_tx.wait(1)
    mint_tx = cube_token.mint(account.address, amount_to_stake, {"from": cube_farm})
    mint_tx.wait(1)
    set_price_feed_tx = cube_farm.setPriceFeedContract(
        cube_token.address,
        get_contract("dai_usd_price_feed"),
        {"from": account},
    )
    set_price_feed_tx.wait(1)
    add_allowed_token_tx = cube_farm.addAllowedToken(
        cube_token.address, {"from": account}
    )
    add_allowed_token_tx.wait(1)
    approve_tx = cube_token.approve(
        cube_farm.address, amount_to_stake, {"from": account}
    )
    approve_tx.wait(1)
    stake_token_tx = cube_farm.stakeTokens(
        amount_to_stake, cube_token.address, {"from": account}
    )
    stake_token_tx.wait(1)
    start_time_when_staked = cube_farm.getUserTokenStartTime(
        account.address, cube_token.address
    )
    # Add rate time (block is mined on the next transaction)
    chain.sleep(RATE)
    unstake_token_tx = cube_farm.unstakeTokens(
        amount_to_stake, cube_token.address, {"from": account}
    )
    unstake_token_tx.wait(1)
    cube_balance_after_unstaking = cube_farm.getUserCubeBalance(account.address) / (
        10**DECIMALS
    )
    start_time_when_unstaked = cube_farm.getUserTokenStartTime(
        account.address, cube_token.address
    )
    # Act
    claim_yield_rewards_tx = cube_farm.claimYieldRewards({"from": account})
    claim_yield_rewards_tx.wait(1)
    expected_rewards = calculate_rewards_based_on_time(
        amount_to_stake,
        INITIAL_PRICE_FEED_VALUE,
        start_time_when_staked,
        start_time_when_unstaked,
    ) / (10**DECIMALS)
    expected_total_value = (amount_to_stake / (10**DECIMALS)) + expected_rewards
    cube_balance = cube_token.balanceOf(account) / (10**DECIMALS)
    # Assert
    # Removing the decimals and asserting with isclose because python and solidity round and can be a bit different
    assert math.isclose(cube_balance_after_unstaking, expected_rewards, rel_tol=REL_TOL)
    assert cube_balance > 0
    assert math.isclose(cube_balance, expected_total_value, rel_tol=REL_TOL)
    assert len(claim_yield_rewards_tx.events["YieldRewarded"]) == 1


def test_can_claim_yield_rewards_after_staking_two_times(amount_to_stake):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Transfer the role to CubeFarm
    minter_role = cube_token.MINTER_ROLE()
    grant_role_tx = cube_token.grantRole(
        minter_role, cube_farm.address, {"from": account}
    )
    grant_role_tx.wait(1)
    mint_tx = cube_token.mint(
        account.address, amount_to_stake + amount_to_stake, {"from": cube_farm}
    )
    mint_tx.wait(1)
    set_price_feed_tx = cube_farm.setPriceFeedContract(
        cube_token.address,
        get_contract("dai_usd_price_feed"),
        {"from": account},
    )
    set_price_feed_tx.wait(1)
    add_allowed_token_tx = cube_farm.addAllowedToken(
        cube_token.address, {"from": account}
    )
    add_allowed_token_tx.wait(1)
    approve_tx = cube_token.approve(
        cube_farm.address, amount_to_stake, {"from": account}
    )
    approve_tx.wait(1)
    stake_token_tx = cube_farm.stakeTokens(
        amount_to_stake, cube_token.address, {"from": account}
    )
    stake_token_tx.wait(1)
    start_time_when_first_staking = cube_farm.getUserTokenStartTime(
        account.address, cube_token.address
    )
    # Add rate time (block is mined on the next transaction)
    chain.sleep(RATE)
    approve_tx = cube_token.approve(
        cube_farm.address, amount_to_stake, {"from": account}
    )
    approve_tx.wait(1)
    stake_token_tx = cube_farm.stakeTokens(
        amount_to_stake, cube_token.address, {"from": account}
    )
    stake_token_tx.wait(1)
    cube_balance_after_second_staking = cube_farm.getUserCubeBalance(
        account.address
    ) / (10**DECIMALS)
    start_time_when_second_staking = cube_farm.getUserTokenStartTime(
        account.address, cube_token.address
    )
    # Add rate time (block is mined on the next transaction)
    chain.sleep(RATE)
    # Act
    claim_yield_rewards_tx = cube_farm.claimYieldRewards({"from": account})
    claim_yield_rewards_tx.wait(1)
    start_time_when_claimed = cube_farm.getUserTokenStartTime(
        account.address, cube_token.address
    )
    # 2000 is staked the first day
    # After 1 day the reward should be 2000
    # 2000 is added the second day -> total 4000 staked
    # After another 1 day the rewards should be the first 2000 + 4000 (of the second day)
    # expected rewards should then be 2000 + 4000
    expected_rewards_first_staking = calculate_rewards_based_on_time(
        amount_to_stake,
        INITIAL_PRICE_FEED_VALUE,
        start_time_when_first_staking,
        start_time_when_second_staking,
    ) / (10**DECIMALS)
    expected_rewards_second_staking = calculate_rewards_based_on_time(
        # Now there is 2 times the amount staked
        amount_to_stake * 2,
        INITIAL_PRICE_FEED_VALUE,
        start_time_when_second_staking,
        start_time_when_claimed,
    ) / (10**DECIMALS)
    expected_rewards = expected_rewards_first_staking + expected_rewards_second_staking
    cube_balance = cube_token.balanceOf(account) / (10**DECIMALS)
    # Assert
    # Removing the decimals and asserting with isclose because python and solidity round and can be a bit different
    assert math.isclose(
        cube_balance_after_second_staking, expected_rewards_first_staking
    )
    assert cube_balance > 0
    assert math.isclose(cube_balance, expected_rewards, rel_tol=REL_TOL)
    assert len(claim_yield_rewards_tx.events["YieldRewarded"]) == 1


def test_can_claim_rewards_after_staking_unstaking_and_staking(amount_to_stake):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENV:
        pytest.skip("Only for local testing")
    account = get_account()
    cube_token, cube_farm = deploy()
    # Transfer the role to CubeFarm
    minter_role = cube_token.MINTER_ROLE()
    grant_role_tx = cube_token.grantRole(
        minter_role, cube_farm.address, {"from": account}
    )
    grant_role_tx.wait(1)
    mint_tx = cube_token.mint(account.address, amount_to_stake, {"from": cube_farm})
    mint_tx.wait(1)
    set_price_feed_tx = cube_farm.setPriceFeedContract(
        cube_token.address,
        get_contract("dai_usd_price_feed"),
        {"from": account},
    )
    set_price_feed_tx.wait(1)
    add_allowed_token_tx = cube_farm.addAllowedToken(
        cube_token.address, {"from": account}
    )
    add_allowed_token_tx.wait(1)
    approve_tx = cube_token.approve(
        cube_farm.address, amount_to_stake, {"from": account}
    )
    approve_tx.wait(1)
    stake_token_tx = cube_farm.stakeTokens(
        amount_to_stake, cube_token.address, {"from": account}
    )
    stake_token_tx.wait(1)
    start_time_when_first_staking = cube_farm.getUserTokenStartTime(
        account.address, cube_token.address
    )
    # Add rate time (block is mined on the next transaction)
    chain.sleep(RATE)
    unstake_token_tx = cube_farm.unstakeTokens(
        amount_to_stake, cube_token.address, {"from": account}
    )
    unstake_token_tx.wait(1)
    cube_balance_after_unstaking = cube_farm.getUserCubeBalance(account.address) / (
        10**DECIMALS
    )
    start_time_when_unstaked = cube_farm.getUserTokenStartTime(
        account.address, cube_token.address
    )
    # Add rate time (block is mined on the next transaction)
    chain.sleep(RATE)
    approveTx = cube_token.approve(
        cube_farm.address, amount_to_stake, {"from": account}
    )
    approveTx.wait(1)
    stake_token_tx = cube_farm.stakeTokens(
        amount_to_stake, cube_token.address, {"from": account}
    )
    stake_token_tx.wait(1)
    start_time_when_second_staking = cube_farm.getUserTokenStartTime(
        account.address, cube_token.address
    )
    # Add rate time (block is mined on the next transaction)
    chain.sleep(RATE)
    # Act
    claim_yield_rewards_tx = cube_farm.claimYieldRewards({"from": account})
    claim_yield_rewards_tx.wait(1)
    start_time_when_claimed = cube_farm.getUserTokenStartTime(
        account.address, cube_token.address
    )
    # 2000 is staked the first day
    # After 1 day the reward should be 2000
    # The total is unstaked all the second day
    # 2000 is staked the third day
    # After another 1 day the rewards should be the first 2000 + 2000 (from the third day)
    # expected rewards should then be 2000 + 2000
    expected_rewards_first_staking = calculate_rewards_based_on_time(
        amount_to_stake,
        INITIAL_PRICE_FEED_VALUE,
        start_time_when_first_staking,
        start_time_when_unstaked,
    ) / (10**DECIMALS)
    expected_rewards_second_staking = calculate_rewards_based_on_time(
        amount_to_stake,
        INITIAL_PRICE_FEED_VALUE,
        start_time_when_second_staking,
        start_time_when_claimed,
    ) / (10**DECIMALS)
    expected_rewards = expected_rewards_first_staking + expected_rewards_second_staking
    cube_balance = cube_token.balanceOf(account) / (10**DECIMALS)
    # Assert
    # Removing the decimals and asserting with isclose because python and solidity round and can be a bit different
    assert math.isclose(
        cube_balance_after_unstaking, expected_rewards_first_staking, rel_tol=REL_TOL
    )
    assert cube_balance > 0
    assert math.isclose(cube_balance, expected_rewards, rel_tol=REL_TOL)
    assert len(claim_yield_rewards_tx.events["YieldRewarded"]) == 1
