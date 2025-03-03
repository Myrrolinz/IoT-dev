<template>
  <div class="chart-container">
    <div ref="chart" class="chart"></div>
  </div>
</template>

<script>
import * as echarts from 'echarts';
import axios from 'axios';

export default {
  props: {
    chartType: String, // e.g., 'co2', 'delta_co2', 'temperature', etc.
    title: String,     // Title for the chart
    location: String,  // Location value e.g., 'location_1'
    indoorOrOutdoor: String // 'indoor' or 'outdoor', optional for non-delta
  },
  mounted() {
    this.initChart();
  },
  methods: {
    async initChart() {
      let data, timestamps, seriesData;
      const location = this.location || 'location_1'; // Default location
      const sensorType = this.chartType.replace('delta_', ''); // Get sensor type without 'delta_'

      try {
        // Determine which API to use based on chartType
        if (this.chartType.startsWith('delta_')) {
          // Use /api/delta/<location>/<sensor_type> route
          const response = await axios.get(`/api/delta/${location}/${sensorType}`);
          data = response.data;

          // Get delta data
          seriesData = data.values; // 'values' contains delta data
          timestamps = data.timestamps;

        } else {
          // Use /api/data/<location>/<sensor_type>/<indoor_or_outdoor> route
          const indoorOrOutdoor = this.indoorOrOutdoor || 'indoor'; // Default to 'indoor'
          const response = await axios.get(`/api/data/${location}/${sensorType}/${indoorOrOutdoor}`);
          data = response.data;

          // Get indoor or outdoor data
          seriesData = data.values;
          timestamps = data.timestamps;
        }

        // Check if data was successfully retrieved
        if (!timestamps || !seriesData) {
          console.error('No data available for chart:', this.chartType);
          return;
        }

        // Log the fetched data for debugging
        console.log('Fetched data:', { timestamps, seriesData });

        // eCharts configuration
        const option = {
          title: {
            text: this.title
          },
          tooltip: {
            trigger: 'axis',
            formatter: (params) => {
              return `${params[0].axisValueLabel}<br />${params[0].seriesName}: ${params[0].value}`;
            }
          },
          xAxis: {
            type: 'category',
            data: timestamps,
            name: 'Time (UTC)',       // Add this line to indicate UTC time
            nameLocation: 'center',
            nameTextStyle: {
              padding: 25            // Adjust padding to position the name properly
            }
          },
          yAxis: {
            type: 'value'
          },
          dataZoom: [                  // Add dataZoom component for zooming functionality
            {
              type: 'inside',          // Enables zooming with mouse wheel and touch gestures
            },
            {
              type: 'slider',          // Adds a slider control to the chart
            }
          ],
          series: [
            {
              name: this.title,
              type: 'line',
              data: seriesData,
              smooth: true,
              connectNulls: false      // Do not connect points with NaNs
            }
          ]
        };

        // Initialize or update the chart
        const chartInstance = echarts.init(this.$refs.chart);
        chartInstance.setOption(option);

        // Log chart initialization for debugging
        console.log('Chart initialized:', chartInstance);
      } catch (error) {
        console.error('Error fetching data for chart:', error);
      }
    }
  }
}
</script>

<style scoped>
.chart-container {
  display: grid;
  place-items: center;
  /* Center horizontally and vertically */
  width: 100%;
  height: 60vh;
  /* Make the container occupy the entire viewport height */
}

.chart {
  width: 100%;
  /* Make the chart responsive */
  height: 100%;
  /* Make the chart responsive */
}
</style>w