import {Box, Flex} from 'grid-emotion';
import PropTypes from 'prop-types';
import React from 'react';
import styled from 'react-emotion';

import {Panel, PanelHeader, PanelBody, PanelItem} from 'app/components/panels';
import {TableChart} from 'app/components/charts/tableChart';
import {t} from 'app/locale';
import AreaChart from 'app/components/charts/areaChart';
import Count from 'app/components/count';
import PercentageBarChart from 'app/components/charts/percentageBarChart';
import IdBadge from 'app/components/idBadge';
import PanelChart from 'app/components/charts/panelChart';
import PieChart from 'app/components/charts/pieChart';
import overflowEllipsis from 'app/styles/overflowEllipsis';
import space from 'app/styles/space';
import theme from 'app/utils/theme';
import withApi from 'app/utils/withApi';
import withLatestContext from 'app/utils/withLatestContext';

import HealthContext from './util/healthContext';
import HealthRequest from './util/healthRequest';

const OrganizationHealthErrors = styled(
  class extends React.Component {
    render() {
      let {className} = this.props;
      return (
        <div className={className}>
          <Flex justify="space-between">
            <Header>Browsers & Operating Systems</Header>
          </Flex>

          <Flex>
            <HealthRequest tag="browser.name" timeseries={false}>
              {({data, loading}) => {
                if (!data) return null;
                return (
                  <StyledPanelChart
                    height={200}
                    series={[
                      {
                        seriesName: t('Browsers'),
                        data: data.map(([name, value]) => ({name, value})),
                      },
                    ]}
                    title={t('Browsers')}
                  >
                    {({series}) => (
                      <Flex>
                        <PieChartWrapper>
                          <PieChart height={300} series={series} />
                        </PieChartWrapper>
                      </Flex>
                    )}
                  </StyledPanelChart>
                );
              }}
            </HealthRequest>
            <HealthRequest tag="os.name" timeseries={false}>
              {({data, loading}) => {
                if (!data) return null;
                return (
                  <StyledPanelChart
                    height={200}
                    series={[
                      {
                        seriesName: t('OS'),
                        data: data.map(([name, value]) => ({name, value})),
                      },
                    ]}
                    title={t('OS')}
                  >
                    {({series}) => (
                      <Flex>
                        <PieChartWrapper>
                          <PieChart height={300} series={series} />
                        </PieChartWrapper>
                      </Flex>
                    )}
                  </StyledPanelChart>
                );
              }}
            </HealthRequest>
          </Flex>

          <Flex>
            <HealthRequest tag="browser.name" timeseries={false} topk={5}>
              {({data, originalData, loading}) => {
                if (!data) return null;

                const total = data.reduce((acc, [, value]) => acc + value, 0);
                const seriesPercentages = data
                  .map(([name, value]) => [name, Math.round(value / total * 10000) / 100])
                  .reduce(
                    (acc, [name, value]) => ({
                      ...acc,
                      [name]: value,
                    }),
                    {}
                  );
                return (
                  <React.Fragment>
                    {!loading && (
                      <Panel style={{width: '100%'}}>
                        <PanelHeader>
                          <Flex
                            flex={1}
                            style={{flexShrink: 0, marginRight: 18}}
                            justify="space-between"
                            align="center"
                          >
                            <span>Browser</span>
                            <span>Events</span>
                          </Flex>
                          <Flex flex={3} justify="space-between" align="center">
                            <span>Percentage</span>
                            <span>Last Event</span>
                          </Flex>
                        </PanelHeader>
                        <PanelBody>
                          {originalData.map(
                            ({count, lastCount, ['browser.name']: name}) => {
                              return (
                                <PanelItem key={name}>
                                  <Flex
                                    flex={1}
                                    style={{flexShrink: 0, marginRight: 18}}
                                    justify="space-between"
                                    align="center"
                                  >
                                    <span>{name}</span>
                                    <span>
                                      {count}

                                      {` (${count > lastCount
                                        ? '+'
                                        : count === lastCount ? '' : '-'}${Math.round(
                                        Math.abs(count - lastCount) / (count + lastCount)
                                      )}%)`}
                                    </span>
                                  </Flex>
                                  <Flex flex={3} justify="space-between" align="center">
                                    <Flex w={[3 / 4]} align="center">
                                      <div
                                        style={{
                                          width: '85%',
                                          marginRight: 6,
                                        }}
                                      >
                                        <div
                                          style={{
                                            flex: 1,
                                            width: `${seriesPercentages[name]}%`,
                                            backgroundColor: '#ccc',
                                            height: 12,
                                            borderRadius: 2,
                                          }}
                                        />
                                      </div>
                                      <span>{seriesPercentages[name]}%</span>
                                    </Flex>
                                    <Flex w={[1 / 4]} justify="flex-end">
                                      <span>5 minutes ago</span>
                                    </Flex>
                                  </Flex>
                                </PanelItem>
                              );
                            }
                          )}
                        </PanelBody>
                      </Panel>
                    )}
                  </React.Fragment>
                );
              }}
            </HealthRequest>
          </Flex>

          <Flex />
        </div>
      );
    }
  }
)``;

const PieChartWrapper = styled(Box)`
  flex: 1;
  flex-shrink: 0;
`;
class OrganizationHealthErrorsContainer extends React.Component {
  render() {
    // Destructure props from `withLatestContext`
    let {
      organizations, // eslint-disable-line
      project, // eslint-disable-line
      lastRoute, // eslint-disable-line
      ...props
    } = this.props;

    return (
      <HealthContext.Consumer>
        {({projects, environments, period}) => (
          <OrganizationHealthErrors
            projects={projects}
            environments={environments}
            period={period}
            {...props}
          />
        )}
      </HealthContext.Consumer>
    );
  }
}

export default withApi(withLatestContext(OrganizationHealthErrorsContainer));

const Header = styled(Flex)`
  font-size: 18px;
  margin-bottom: ${space(2)};
`;

const SubduedCount = styled('span')`
  color: ${p => p.theme.gray1};
  margin-left: ${space(0.5)};
`;

const getChartMargin = () => `
  margin-right: ${space(2)};
  &:last-child {
    margin-right: 0;
  }
`;

const StyledPanelChart = styled(PanelChart)`
  ${getChartMargin};
  flex-shrink: 0;
  overflow: hidden;
`;

const StyledTableChart = styled(TableChart)`
  ${getChartMargin};
  flex-shrink: 0;
  overflow: hidden;
`;

const ReleaseName = styled(Box)`
  ${overflowEllipsis};
`;

const Project = styled(Box)`
  margin-left: ${space(1)};
  flex-shrink: 0;
`;
