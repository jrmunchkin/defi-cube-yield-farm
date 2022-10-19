// SPDX-License-identifier: MIT

pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockLINK is ERC20 {
    constructor() ERC20("Mock LINK", "LINK") {}
}
