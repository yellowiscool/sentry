import {Box, Flex} from 'grid-emotion';
import PropTypes from 'prop-types';
import React from 'react';
import styled from 'react-emotion';

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
            <Header>
              Errors
              <SubduedCount>
                (<Count value={12198} />)
              </SubduedCount>
            </Header>
          </Flex>

          <Flex>
            <HealthRequest
              tag="error.handled"
              timeseries={true}
              interval="1d"
              getCategory={handled => (handled ? 'Handled' : 'Crash')}
            >
              {({data, loading}) => {
                if (!data) return null;
                console.log('handled', data);
                return (
                  <StyledPanelChart height={200} title={t('Errors')} series={data}>
                    {props => <AreaChart {...props} />}
                  </StyledPanelChart>
                );
              }}
            </HealthRequest>

            <HealthRequest
              tag="release"
              timeseries={true}
              interval="1d"
              getCategory={({shortVersion}) => shortVersion}
            >
              {({data, loading}) => {
                if (!data) return null;
                return (
                  <StyledPanelChart height={200} title={t('Releases')} series={data}>
                    {props => <PercentageBarChart {...props} />}
                  </StyledPanelChart>
                );
              }}
            </HealthRequest>
          </Flex>

          <Flex>
            <HealthRequest tag="error.type" timeseries={false} interval="1d">
              {({data, loading}) => {
                if (!data) return null;
                return (
                  <StyledTableChart
                    title="Error Type"
                    headers={['Error type']}
                    data={data}
                    widths={[null, 60, 60, 60, 60]}
                    showColumnTotal
                    shadeRowPercentage
                  />
                );
              }}
            </HealthRequest>
            <HealthRequest
              tag="user"
              timeseries={false}
              getCategory={({user}) => user.label}
            >
              {({originalData, loading}) => (
                <React.Fragment>
                  {!loading && (
                    <StyledTableChart
                      headers={[t('Most Impacted')]}
                      data={originalData.map(row => [row, row])}
                      widths={[null, 120]}
                      getValue={item =>
                        typeof item === 'number' ? item : item && item.count}
                      renderHeaderCell={({getValue, value, columnIndex}) => {
                        return typeof value === 'string' ? (
                          value
                        ) : (
                          <IdBadge
                            user={value.user}
                            displayName={value.user && value.user.label}
                          />
                        );
                      }}
                      renderDataCell={({getValue, value, columnIndex}) => {
                        return <Count value={getValue(value)} />;
                      }}
                      showRowTotal={false}
                      showColumnTotal={false}
                      shadeRowPercentage
                    />
                  )}
                </React.Fragment>
              )}
            </HealthRequest>
          </Flex>

          <Flex>
            <HealthRequest
              tag="release"
              timeseries={false}
              topk={5}
              getCategory={({shortVersion}) => shortVersion}
            >
              {({originalData: data, loading}) => {
                return (
                  <React.Fragment>
                    {!loading && (
                      <React.Fragment>
                        <StyledTableChart
                          headers={[t('Errors by Release')]}
                          data={data.map(row => [row, row])}
                          widths={[null, 120]}
                          getValue={item =>
                            typeof item === 'number' ? item : item && item.count}
                          renderHeaderCell={({getValue, value, columnIndex}) => {
                            return (
                              <Flex justify="space-between">
                                <ReleaseName>{value.release.version}</ReleaseName>
                                <Project>
                                  {value.topProjects.map(p => (
                                    <IdBadge key={p.slug} project={p} />
                                  ))}
                                </Project>
                              </Flex>
                            );
                          }}
                          renderDataCell={({getValue, value, columnIndex}) => {
                            return <Count value={getValue(value)} />;
                          }}
                          showRowTotal={false}
                          showColumnTotal={false}
                          shadeRowPercentage
                        />
                        <StyledPanelChart
                          height={300}
                          title={t('Errors By Release')}
                          showLegend={false}
                          data={data.map(row => ({
                            name: row.release.version,
                            value: row.count,
                          }))}
                        >
                          {({data: panelData}) => (
                            <Flex>
                              <LegendWrapper>
                                <Legend data={panelData} />
                              </LegendWrapper>
                              <PieChartWrapper>
                                <PieChart height={300} data={panelData} />
                              </PieChartWrapper>
                            </Flex>
                          )}
                        </StyledPanelChart>
                      </React.Fragment>
                    )}
                  </React.Fragment>
                );
              }}
            </HealthRequest>
          </Flex>

          <Flex>
            <HealthRequest tag="browser.name" timeseries={false}>
              {({data, loading}) => {
                if (!data) return null;
                return (
                  <StyledPanelChart
                    height={200}
                    data={data.map(([name, value]) => ({name, value}))}
                    title={t('Browsers')}
                  >
                    {({data: panelData}) => (
                      <Flex>
                        <LegendWrapper>
                          <Legend data={panelData} />
                        </LegendWrapper>
                        <PieChartWrapper>
                          <PieChart height={300} data={panelData} />
                        </PieChartWrapper>
                      </Flex>
                    )}
                  </StyledPanelChart>
                );
              }}
            </HealthRequest>
          </Flex>
        </div>
      );
    }
  }
)``;

const PieChartWrapper = styled(Box)`
  flex: 1;
  flex-shrink: 0;
`;
const LegendWrapper = styled(Box)`
  flex: 1;
  padding: ${space(2)};
  overflow: hidden;
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
class Legend extends React.Component {
  static propTypes = {
    data: PropTypes.array,
  };

  render() {
    let {data} = this.props;
    return (
      <Flex direction="column">
        {data.map((item, i) => {
          return (
            <LegendRow key={i}>
              <Square
                size={16}
                color={theme.charts.colors[i % theme.charts.colors.length]}
              />
              <ReleaseName>{item.name}</ReleaseName>
            </LegendRow>
          );
        })}
      </Flex>
    );
  }
}

const Square = styled('div')`
  width: ${p => p.size}px;
  height: ${p => p.size}px;
  border-radius: ${p => p.theme.borderRadius};
  background-color: ${p => p.color};
  margin-right: ${space(1)};
  flex-shrink: 0;
`;

const LegendRow = styled(Flex)`
  margin: ${space(1)};
  align-items: center;
`;
