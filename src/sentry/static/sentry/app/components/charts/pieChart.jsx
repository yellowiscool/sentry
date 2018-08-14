import React from 'react';

import Legend from './components/legend';
import PieSeries from './series/pieSeries';
import BaseChart from './baseChart';

class PieChart extends React.Component {
  static propTypes = {
    // We passthrough all props exception `options`
    ...BaseChart.propTypes,
  };

  // echarts Legend does not have access to percentages (but tooltip does :/)
  getSeriesPercentages = series => {
    const total = series.data.reduce((acc, {value}) => acc + value, 0);
    return series.data
      .map(({name, value}) => [name, Math.round(value / total * 10000) / 100])
      .reduce(
        (acc, [name, value]) => ({
          ...acc,
          [name]: value,
        }),
        {}
      );
  };

  render() {
    const {series, ...props} = this.props;
    if (!series || !series.length) return null;
    if (series.length > 1) {
      // eslint-disable-next-line no-console
      console.warn('PieChart only uses the first series!');
    }

    // Note, we only take the first series unit!
    const [firstSeries] = series;
    const seriesPercentages = this.getSeriesPercentages(firstSeries);

    return (
      <BaseChart
        {...props}
        options={{
          legend: Legend({
            orient: 'vertical',
            align: 'left',
            show: true,
            left: 10,
            top: 10,
            bottom: 10,
            formatter: name => {
              return `${name} ${typeof seriesPercentages[name] !== 'undefined'
                ? `(${seriesPercentages[name]}%)`
                : ''}`;
            },
          }),
          series: [
            PieSeries({
              name: firstSeries.seriesName,
              data: firstSeries.data,
              avoidLabelOverlap: false,
              label: {
                normal: {
                  formatter: '{b}\n{d}%',
                  show: false,
                  position: 'center',
                },
                emphasis: {
                  show: true,
                  textStyle: {
                    fontSize: '18',
                  },
                },
              },
              itemStyle: {
                normal: {
                  label: {
                    show: false,
                  },
                  labelLine: {
                    show: false,
                  },
                },
              },
            }),
          ],
        }}
      />
    );
  }
}

export default PieChart;
