// migrations/2_deploy_nids_logger.js
// Deploys the NIDSLogger smart contract to Ganache

const NIDSLogger = artifacts.require("NIDSLogger");

module.exports = function (deployer) {
  deployer.deploy(NIDSLogger);
};
