import {Flex} from 'grid-emotion';
import React from 'react';
import styled from 'react-emotion';

import {t} from 'app/locale';
import PanelChart from 'app/components/charts/panelChart';
import PieChart from 'app/components/charts/pieChart';
import space from 'app/styles/space';
import withApi from 'app/utils/withApi';
import withLatestContext from 'app/utils/withLatestContext';

import HealthContext from './util/healthContext';
import HealthRequest from './util/healthRequest';
import EventsTableChart from './eventsTableChart';

const OrganizationHealthErrors = styled(
  class extends React.Component {
    render() {
      let {className} = this.props;
      return (
        <div className={className}>
          <Flex justify="space-between">
            <Header>Devices</Header>
          </Flex>

          <HealthRequest tag="device" timeseries={false} topk={5}>
            {({data, originalData, tag, loading}) => {
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
                  <Flex>
                    <StyledPanelChart
                      height={200}
                      showLegend={false}
                      series={[
                        {
                          data: data.map(([name, value]) => ({name, value})),
                        },
                      ]}
                      title={t('Devices')}
                    >
                      {({series}) => <PieChart height={300} series={series} />}
                    </StyledPanelChart>
                  </Flex>

                  <Flex>
                    <EventsTableChart
                      headers={[
                        t('Device'),
                        t('Events'),
                        t('Percentage'),
                        t('Last event'),
                      ]}
                      data={originalData.map(({count, lastCount, [tag]: name}) => ({
                        count,
                        lastCount,
                        name,
                        percentage: seriesPercentages[name],
                      }))}
                    />
                  </Flex>
                </React.Fragment>
              );
            }}
          </HealthRequest>
        </div>
      );
    }
  }
)``;

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
