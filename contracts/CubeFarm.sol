// SPDX-License-identifier: MIT

pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";
import "./CubeToken.sol";

error CubeFarm__CannotStakeAmountZero();
error CubeFarm__TokenNotAllowed();
error CubeFarm__CannotUnStakeZeroBalance();
error CubeFarm__CannotUnStakeMoreThanUserBalance();
error CubeFarm__NoRewardsToTransfer();
error CubeFarm__ExternalCallFailed();

/**
 * @title CubeFarm
 * @author jrchain
 * @notice This contract creates a simple yield farming defi that rewards users for staking up their differents token with a new ERC20 token CubeToken.
 * @dev The constructor takes the address of the CubeToken ERC20 and a rate.
 * The rate is used in the algorithm to calculate the rewards that should be distributed to the user.
 * The rate represents the time in seconds to be rewarded by 100% of the amount staked.
 * For example if the rate is 86400 seconds (1 day) and the amount staked is 1 ether, then the reward will be 1 ether (in CubeToken) after 1 day of staking.
 * Ownership of the CubeToken contract should be transferred to the CubeFarm contract after deployment.
 * This contract also implements the Chainlink price feed.
 */
contract CubeFarm is Ownable {
    CubeToken private immutable i_cubeToken;
    uint256 private immutable i_rate;
    address[] private s_allowedTokens;
    address[] private s_stakers;
    mapping(address => uint256) private s_uniqueTokensStaked;
    mapping(address => address) private s_tokenPriceFeeds;
    mapping(address => uint256) private s_cubeBalance;
    mapping(address => mapping(address => uint256)) private s_stakingBalance;
    mapping(address => mapping(address => uint256)) private s_startTime;

    event TokenStaked(
        address indexed token,
        address indexed staker,
        uint256 amount
    );
    event TokenUnstaked(
        address indexed token,
        address indexed staker,
        uint256 amount
    );
    event YieldRewarded(address indexed staker, uint256 rewards);

    /**
     * @notice contructor
     * @param _cubeTokenAddress CubeToken contract address
     * @param _rate rate in seconds for calculating the rewards
     */
    constructor(CubeToken _cubeTokenAddress, uint256 _rate) {
        i_cubeToken = _cubeTokenAddress;
        i_rate = _rate;
    }

    /**
     * @notice Set the price feed for a specific token
     * @param _token token address
     * @param _priceFeedAddress price feed address
     */
    function setPriceFeedContract(address _token, address _priceFeedAddress)
        external
        onlyOwner
    {
        s_tokenPriceFeeds[_token] = _priceFeedAddress;
    }

    /**
     * @notice Add a token to the allowed tokens list
     * @param _token token address to add to the list
     */
    function addAllowedToken(address _token) external onlyOwner {
        s_allowedTokens.push(_token);
    }

    /**
     * @notice Allow user to stake tokens
     * @param _amount amount to stake
     * @param _token address of the token to stake
     * @dev emit an event TokenStaked when token is staked
     */
    function stakeTokens(uint256 _amount, address _token) external {
        if (_amount <= 0 || IERC20(_token).balanceOf(msg.sender) < _amount)
            revert CubeFarm__CannotStakeAmountZero();
        if (!isTokenAllowed(_token)) revert CubeFarm__TokenNotAllowed();
        if (s_stakingBalance[_token][msg.sender] <= 0)
            s_uniqueTokensStaked[msg.sender]++;
        if (s_stakingBalance[_token][msg.sender] > 0) {
            uint256 toTransfer = getUserYieldRewardsByToken(msg.sender, _token);
            s_cubeBalance[msg.sender] += toTransfer;
        }
        s_stakingBalance[_token][msg.sender] =
            s_stakingBalance[_token][msg.sender] +
            _amount;
        if (s_uniqueTokensStaked[msg.sender] == 1) s_stakers.push(msg.sender);
        s_startTime[_token][msg.sender] = block.timestamp;
        bool success = IERC20(_token).transferFrom(
            msg.sender,
            address(this),
            _amount
        );
        if (!success) revert CubeFarm__ExternalCallFailed();
        emit TokenStaked(_token, msg.sender, _amount);
    }

    /**
     * @notice Allow user to unstake tokens
     * @param _amount amount to unstake
     * @param _token address of the token to unstake
     * @dev emit an event TokenUnstaked when token is unstaked
     */
    function unstakeTokens(uint256 _amount, address _token) external {
        uint256 userBalance = s_stakingBalance[_token][msg.sender];
        if (userBalance <= 0) revert CubeFarm__CannotUnStakeZeroBalance();
        if (_amount > userBalance)
            revert CubeFarm__CannotUnStakeMoreThanUserBalance();
        uint256 toTransfer = getUserYieldRewardsByToken(msg.sender, _token);
        s_startTime[_token][msg.sender] = block.timestamp;
        s_stakingBalance[_token][msg.sender] -= _amount;
        s_cubeBalance[msg.sender] += toTransfer;
        if (s_stakingBalance[_token][msg.sender] == 0)
            s_uniqueTokensStaked[msg.sender]--;
        if (s_uniqueTokensStaked[msg.sender] == 0) {
            for (
                uint256 stakersIndex = 0;
                stakersIndex < s_stakers.length;
                stakersIndex++
            ) {
                if (s_stakers[stakersIndex] == msg.sender) {
                    s_stakers[stakersIndex] = s_stakers[s_stakers.length - 1];
                    s_stakers.pop();
                }
            }
        }
        bool success = IERC20(_token).transfer(msg.sender, _amount);
        if (!success) revert CubeFarm__ExternalCallFailed();
        emit TokenUnstaked(_token, msg.sender, _amount);
    }

    /**
     * @notice Allow user to claim his rewards
     * @dev emit an event YieldRewarded when rewards have been claimed
     */
    function claimYieldRewards() external {
        uint256 toTransfer = getUserTotalYieldRewards(msg.sender);
        if (s_cubeBalance[msg.sender] != 0) {
            uint256 oldBalance = s_cubeBalance[msg.sender];
            s_cubeBalance[msg.sender] = 0;
            toTransfer += oldBalance;
        }
        for (
            uint256 allowedTokenIndex;
            allowedTokenIndex < s_allowedTokens.length;
            allowedTokenIndex++
        ) {
            s_startTime[s_allowedTokens[allowedTokenIndex]][msg.sender] = block
                .timestamp;
        }
        if (toTransfer <= 0) revert CubeFarm__NoRewardsToTransfer();
        i_cubeToken.mint(msg.sender, toTransfer);
        emit YieldRewarded(msg.sender, toTransfer);
    }

    /**
     * @notice Check if the token is allowed
     * @param _token address of the token to check
     * @return isAllowed true if allowed, false ether
     */
    function isTokenAllowed(address _token) internal returns (bool) {
        for (
            uint256 allowedTokenIndex = 0;
            allowedTokenIndex < s_allowedTokens.length;
            allowedTokenIndex++
        ) {
            if (s_allowedTokens[allowedTokenIndex] == _token) return true;
        }
        return false;
    }

    /**
     * @notice Get the user total yield rewards
     * @param _user address of the user
     * @return totalYieldReward total yield rewards of user
     */
    function getUserTotalYieldRewards(address _user)
        internal
        view
        returns (uint256)
    {
        uint256 totalYieldReward = 0;
        for (
            uint256 allowedTokenIndex;
            allowedTokenIndex < s_allowedTokens.length;
            allowedTokenIndex++
        ) {
            totalYieldReward =
                totalYieldReward +
                getUserYieldRewardsByToken(
                    _user,
                    s_allowedTokens[allowedTokenIndex]
                );
        }

        return totalYieldReward;
    }

    /**
     * @notice Get the user rewards by token
     * @param _user address of the user
     * @param _token address of the token
     * @return rewards total rewards by specific token
     */
    function getUserYieldRewardsByToken(address _user, address _token)
        internal
        view
        returns (uint256)
    {
        if (s_uniqueTokensStaked[_user] <= 0) return 0;
        (uint256 price, uint256 decimals) = getTokenValue(_token);
        uint256 time = calculateYieldTime(_user, _token) * (10**decimals);
        uint256 timeRate = time / i_rate;
        uint256 stakingPrice = ((s_stakingBalance[_token][_user] * price) /
            (10**decimals));
        return ((stakingPrice * timeRate) / (10**decimals));
    }

    /**
     * @notice Get the last known value of the token thanks to Chainlink price feed
     * @param _token address of the token
     * @return price the last price
     * @return decimals decimals of the price
     * @dev Implements Chainlink price feed
     */
    function getTokenValue(address _token)
        internal
        view
        returns (uint256, uint256)
    {
        address priceFeedAddress = s_tokenPriceFeeds[_token];
        AggregatorV3Interface priceFeed = AggregatorV3Interface(
            priceFeedAddress
        );
        (, int256 price, , , ) = priceFeed.latestRoundData();
        uint256 decimals = priceFeed.decimals();

        return (uint256(price), uint256(decimals));
    }

    /**
     * @notice Calculate since how long the user stake a specific token
     * @param _user address of the user to check
     * @param _token address of the token to check
     * @return totalTime time since the user start to stake this token
     */
    function calculateYieldTime(address _user, address _token)
        internal
        view
        returns (uint256)
    {
        uint256 end = block.timestamp;
        uint256 totalTime = end - s_startTime[_token][_user];
        return totalTime;
    }

    /**
     * @notice Get the total of pending rewards of a specific user
     * @param _user address of the user
     * @return totalPendingRewards total of pending rewards
     */
    function getTotalPendingRewards(address _user)
        external
        view
        returns (uint256)
    {
        return getUserTotalYieldRewards(_user) + s_cubeBalance[_user];
    }

    /**
     * @notice Get Cube token address
     * @return cubeTokenAddress Cube token address
     */
    function getCubeTokenAddress() external view returns (address) {
        return address(i_cubeToken);
    }

    /**
     * @notice Get the rate
     * @return rate rate
     */
    function getRate() external view returns (uint256) {
        return i_rate;
    }

    /**
     * @notice Get the price feed address of a specific token
     * @param _token address of the token
     * @return priceFeedAddress price feed address
     */
    function getPriceFeedContract(address _token)
        external
        view
        returns (address)
    {
        return s_tokenPriceFeeds[_token];
    }

    /**
     * @notice Get the balance of a specific token staked by a user
     * @param _user address of the user
     * @param _token address of the token
     * @return balance balance staked
     */
    function getUserTokenBalance(address _user, address _token)
        external
        view
        returns (uint256)
    {
        return s_stakingBalance[_token][_user];
    }

    /**
     * @notice Get the number of different tokens a user stake
     * @param _user address of the user
     * @return numberOfTokens number of tokens
     */
    function getNumberOfTokenStaked(address _user)
        external
        view
        returns (uint256)
    {
        return s_uniqueTokensStaked[_user];
    }

    /**
     * @notice Get the start time of last staking by a user on a specific token
     * @param _user address of the user
     * @param _token address of the token
     * @return startTime start time from last staking
     */
    function getUserTokenStartTime(address _user, address _token)
        external
        view
        returns (uint256)
    {
        return s_startTime[_token][_user];
    }

    /**
     * @notice Get Cube balance of a specific user
     * @param _user address of the user
     * @return cubeBalance Cube balance
     */
    function getUserCubeBalance(address _user) external view returns (uint256) {
        return s_cubeBalance[_user];
    }

    /**
     * @notice Get the list of stakers
     * @return stakers address list of stakers
     */
    function getStakers() external view returns (address[] memory) {
        return s_stakers;
    }

    /**
     * @notice Get the list of allowed tokens
     * @return allowedTokens address list of allowed tokens
     */
    function getAllowedTokens() external view returns (address[] memory) {
        return s_allowedTokens;
    }
}
