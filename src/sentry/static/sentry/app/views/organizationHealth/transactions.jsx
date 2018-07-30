import {Flex, Box} from 'grid-emotion';
import PropTypes from 'prop-types';
import React from 'react';
import styled from 'react-emotion';

import {t} from 'app/locale';
import AsyncView from 'app/views/asyncView';
import Feature from 'app/components/feature';
import HeaderSeparator from 'app/components/organizations/headerSeparator';
import HealthNavigationMenu from 'app/views/organizationHealth/healthNavigationMenu';
import MultipleProjectSelector from 'app/components/organizations/multipleProjectSelector';
import TimeRangeSelector from 'app/components/organizations/timeRangeSelector';
import withOrganization from 'app/utils/withOrganization';

class OrganizationHealthTransactions extends React.Component {
  render() {
    let {organization, children} = this.props;
    return <div>Transactions</div>;
  }
}

export default withOrganization(OrganizationHealthTransactions);

const Header = styled(Flex)`
  font-size: 18px;
`;

const Body = styled(Flex)``;
