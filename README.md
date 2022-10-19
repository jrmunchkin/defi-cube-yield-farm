# Cube Farm contracts

This is a repository to work with and create a defi yield farm name Cube Farm in a python environment.
This is a backend repository, it also work with a [frontend repository](https://github.com/jrchain/defi-cube-yield-farm-front-end). However you absolutly can use this repository without the frontend part.

## Summary

There is 2 mains contracts:

- The Cube Token : A ERC20 token with the specificity that only the address with Minter role can mint the token.
- The Cube Farm : The yield farming defi contract.

The Cube Farm allow you to :

- `stakeTokens`: Add any approved token to the Cube Farm contract for yiel farming.
- `UnstakeTokens`: Remove your tokens from the Cube Farm contract.
- `clainYieldRewards`: Get rewarded with CUBE tokens calculated with a giving rate and the Chainlink price feed. The rate represents the time in seconds to be rewarded by 100% of the total amount staked. For example if the rate is 86400 seconds (1 day) and the amount staked is 1 ether, then the reward will be 1 ether (in CUBE) after 1 day of staking.
- `getTotalPendingRewards`: Get the total pending CUBE rewards the user can claim.

- [Cube Farm](#cube-farm-contracts)
  - [Summary](#summary)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Testnet Development](#testnet-development)
  - [Local Development](#local-development)
- [Usage](#useage)
  - [Scripts](#scripts)
  - [Testing](#testing)

## Prerequisites

Please install or have installed the following:

- [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- [nodejs and npm](https://nodejs.org/en/download/)
- [python](https://www.python.org/downloads/)

## Installation

1. [Install Brownie](https://eth-brownie.readthedocs.io/en/stable/install.html)

2. Clone this repository

```
git clone https://github.com/jrchain/defi-cube-yield-farm
cd defi-cube-yield-farm
```

## Testnet Development

If you want to be able to deploy to testnets, do the following. I suggest to use goerli network.

```bash
cp .env.exemple .env
```

Set your `WEB3_ALCHEMY_PROJECT_ID`, and `PRIVATE_KEY`

You can get a `WEB3_ALCHEMY_PROJECT_ID` by opening an account at [Alchemy](https://www.alchemy.com/). Follow the steps to create a new application.

You will need to change the provider in brownie (by default works with [Infura](https://infura.io/)).

```bash
brownie networks set_provider alchemy
```

If you still want to use Infura, feel free to replace `WEB3_ALCHEMY_PROJECT_ID` by `WEB3_INFURA_PROJECT_ID` and put your Infura project ID.

You can find your `PRIVATE_KEY` from your ethereum wallet like [metamask](https://metamask.io/).

You'll also want an [Etherscan API Key](https://etherscan.io/apis) to verify your smart contracts. Set it here `ETHERSCAN_TOKEN`.

If you want to use it with the [frontend repository](https://github.com/jrchain/defi-cube-yield-farm-front-end), You also can clone it and set your frontend path `FRONT_END_FOLDER`

You can add your environment variables to the `.env` file:

```bash
export WEB3_ALCHEMY_PROJECT_ID=<PROJECT_ID>
export PRIVATE_KEY=<PRIVATE_KEY>
export ETHERSCAN_TOKEN=<YOUR_TOKEN>
export FRONT_END_FOLDER=<YOUR_PATH_TO_FRONTEND>
```

You'll also need testnet goerli ETH if you want to deploy on goerli tesnet. You can get ETH into your wallet by using the [alchemy goerli faucet](https://goerlifaucet.com/) or [chainlink faucet](https://faucets.chain.link/).

## Local Development

For local testing [install ganache-cli](https://www.npmjs.com/package/ganache-cli)

```bash
npm install -g ganache-cli
```

# Usage

## Scripts

Feel free to change the RATE variable in the helper.py if you want your rate to be more than 1 day.

To deploy the contracts

```bash
brownie run scripts/deploy.py
```

To deploy the contracts on goerli tesnet

```bash
brownie run scripts/deploy.py --network goerli
```

You also have a script to wrap some ETH to WETH (only for tesnet)

```bash
brownie run scripts/get_weth.py --network goerli
```

To update the front end repository with the newly deployed contracts (You need to pull the [frontend](https://github.com/jrchain/defi-cube-yield-farm-front-end) and set your `FRONT_END_FOLDER` first)

```bash
brownie run scripts/update_frontend.py
```

## Testing

For unit testing

```
brownie test
```

For integration testing

```
brownie test --network goerli
```
