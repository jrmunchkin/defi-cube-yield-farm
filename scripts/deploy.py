from brownie import CubeToken, CubeFarm, network, config
from scripts.helper import (
    get_contract,
    get_account,
    RATE,
)


def main():
    deploy()
    setup_cube_farm()


def deploy():
    cube_token = deploy_cube_token()
    cube_farm = deploy_cube_farm(cube_token)
    return cube_token, cube_farm


def deploy_cube_token():
    account = get_account()
    cube_token = CubeToken.deploy(
        {"from": account},
        publish_source=config["networks"][network.show_active()].get("verify", False),
    )
    return cube_token


def deploy_cube_farm(cube_token):
    account = get_account()
    cube_farm = CubeFarm.deploy(
        cube_token.address,
        RATE,
        {"from": account},
        publish_source=config["networks"][network.show_active()].get("verify", False),
    )
    return cube_farm


def setup_cube_farm():
    account = get_account()
    cube_token = CubeToken[-1]
    cube_farm = CubeFarm[-1]
    # Add the allowed tokens and their price feed
    dict_allowed_tokens = {
        get_contract("weth_token"): get_contract("eth_usd_price_feed"),
        get_contract("fau_token"): get_contract("dai_usd_price_feed"),
        get_contract("link_token"): get_contract("link_usd_price_feed"),
        cube_token: get_contract("dai_usd_price_feed"),
    }
    for allowed_token in dict_allowed_tokens:
        allowedTokenTx = cube_farm.addAllowedToken(
            allowed_token.address, {"from": account}
        )
        allowedTokenTx.wait(1)
        setPriceFeedTx = cube_farm.setPriceFeedContract(
            allowed_token.address, dict_allowed_tokens[allowed_token], {"from": account}
        )
        setPriceFeedTx.wait(1)
    # Transfer the minter role to CubeFarm
    minter_role = cube_token.MINTER_ROLE()
    grantTx = cube_token.grantRole(minter_role, cube_farm.address, {"from": account})
    grantTx.wait(1)
