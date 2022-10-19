from brownie import (
    accounts,
    network,
    config,
    Contract,
    MockDAI,
    MockWETH,
    MockLINK,
    MockV3Aggregator,
)

FORKED_BLOCKCHAIN_ENV = ["mainnet-fork"]
LOCAL_BLOCKCHAIN_ENV = ["development", "ganache-local"]

contract_to_mock = {
    "fau_token": MockDAI,
    "weth_token": MockWETH,
    "link_token": MockLINK,
    "eth_usd_price_feed": MockV3Aggregator,
    "dai_usd_price_feed": MockV3Aggregator,
    "link_usd_price_feed": MockV3Aggregator,
}

INITIAL_PRICE_FEED_VALUE = 2000000000000000000000
DECIMALS = 18
RATE = 86400


def get_account(index=None, id=None):
    if index:
        return accounts[index]
    if id:
        return accounts.load(id)
    if (
        network.show_active() in LOCAL_BLOCKCHAIN_ENV
        or network.show_active() in FORKED_BLOCKCHAIN_ENV
    ):
        return accounts[0]
    return accounts.add(config["wallets"]["from_key"])


def get_contract(contract_name):
    contract_type = contract_to_mock[contract_name]
    if network.show_active() in LOCAL_BLOCKCHAIN_ENV:
        if len(contract_type) <= 0:
            deploy_mocks()
        contract = contract_type[-1]
    else:
        contract_address = config["networks"][network.show_active()][contract_name]
        contract = Contract.from_abi(
            contract_type._name, contract_address, contract_type.abi
        )
    return contract


def deploy_mocks(decimals=DECIMALS, initial_value=INITIAL_PRICE_FEED_VALUE):
    account = get_account()
    print("Deploying Mocks...")
    print("Deploying Mock price feed...")
    mock_price_feed = MockV3Aggregator.deploy(
        decimals, initial_value, {"from": account}
    )
    print(f"Deployed to {mock_price_feed.address}")
    print("Deploying Mock DAI...")
    mock_dai = MockDAI.deploy({"from": account})
    print(f"Deployed to {mock_dai.address}")
    print("Deploying Mock WETH...")
    mock_weth = MockWETH.deploy({"from": account})
    print(f"Deployed to {mock_weth.address}")
    print("Deploying Mock LINK...")
    mock_link = MockLINK.deploy({"from": account})
    print(f"Deployed to {mock_link.address}")


def calculate_rewards_based_on_time(
    amount_to_stake, price, start_time, end_time, decimals=DECIMALS
):
    time_passed = (end_time - start_time) * (10**decimals)
    time_rate = time_passed / RATE
    staking_price = (amount_to_stake * price) / (10**decimals)
    return (staking_price * time_rate) / (10**decimals)
