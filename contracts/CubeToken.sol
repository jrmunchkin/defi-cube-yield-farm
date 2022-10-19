// SPDX-License-identifier: MIT

pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

error CubeToken__SenderIsNotTheMinter();

/**
 * @title CubeToken
 * @author jrchain
 * @notice A simple ERC20 token.
 */
contract CubeToken is ERC20, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    /**
     * @notice contructor
     */
    constructor() ERC20("Cube Token", "CUBE") {
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    /**
     * @notice Allow owner to mint tokens
     * @param _to address of the owner
     * @param _amount amount to mint
     */
    function mint(address _to, uint256 _amount) external {
        if (!hasRole(MINTER_ROLE, msg.sender))
            revert CubeToken__SenderIsNotTheMinter();
        _mint(_to, _amount);
    }
}
