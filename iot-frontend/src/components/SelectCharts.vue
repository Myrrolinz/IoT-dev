<template>
  <div class="container">
    <h1>Sensor Data Charts</h1>
    <div class="selectors">
      <label for="location-select">Location:</label>
      <select id="location-select" v-model="selectedLocation" @change="() => { updateSensorOptions(); fetchData(); }">
        <option v-for="location in locations" :key="location" :value="location">
          {{ location }}
        </option>
      </select>

      <label for="sensor-select">Sensor Type:</label>
      <select id="sensor-select" v-model="selectedSensor" @change="fetchData">
        <option v-for="sensor in sensors" :key="sensor" :value="sensor">
          {{ sensor }}
        </option>
      </select>

      <label for="indoor-sensor-select">Indoor Sensor:</label>
      <select id="indoor-sensor-select" v-model="selectedIndoorSensor" @change="fetchData">
        <option value="None">None</option>
        <option v-for="indoor in indoorSensorOptions" :key="indoor" :value="indoor">
          {{ indoor }}
        </option>
      </select>

      <label for="outdoor-sensor-select">Outdoor Sensor:</label>
      <select id="outdoor-sensor-select" v-model="selectedOutdoorSensor" @change="fetchData">
        <option value="None">None</option>
        <option v-for="outdoor in outdoorSensorOptions" :key="outdoor" :value="outdoor">
          {{ outdoor }}
        </option>
      </select>

      <!-- Delta checkbox -->
      <div>
        <input type="checkbox" id="delta-checkbox" v-model="showDelta" @change="fetchData" />
        <label for="delta-checkbox">Show Delta</label>
      </div>

      <!-- Range selection -->
      <!-- <label for="range-select">Time Range (days):</label>
      <select id="range-select" v-model="selectedRangeDays" @change="fetchData">
        <option v-for="d in possibleRanges" :key="d" :value="d">{{ d }} days</option>
      </select> -->
      <!-- Time selection -->
      <div>
        <label for="start-date">Start Date:</label>
        <input type="date" id="start-date" v-model="startDate" @change="fetchData">
      </div>
      <div>
        <label for="end-date">End Date:</label>
        <input type="date" id="end-date" v-model="endDate" @change="fetchData">
      </div>
    </div>

    <div id="chart" style="width: 100%; height: 400px;"></div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import * as echarts from 'echarts';
import axios from 'axios';
import apiClient from '@/services/api.js';

export default {
  props: {
    initialLocation: {
      type: String,
      default: 'Kendeda'
    },
    initialIndoorSensor: {
      type: String,
      default: 'None'
    },
    initialOutdoorSensor: {
      type: String,
      default: 'None'
    }
  },
  setup(props) {
    // We'll store the fetched locationSensorMap here:
    const locationSensorMap = ref({});

    const locations = ref([]);
    const sensors = ref(['co2', 'humidity', 'temperature', 'pressure']);

    const indoorSensorOptions = ref([]);
    const outdoorSensorOptions = ref([]);

    const selectedLocation = ref(props.initialLocation);
    const selectedSensor = ref('co2');

    // Default to None for indoor/outdoor (no raw data shown)
    const selectedIndoorSensor = ref(props.initialIndoorSensor);
    const selectedOutdoorSensor = ref(props.initialOutdoorSensor);


    // Delta checkbox
    const showDelta = ref(true); // default show delta

    /* // Time range selection
    const possibleRanges = ref([1, 3, 7, 14, 30, 60]);
    const selectedRangeDays = ref(7); */
    // Time selection
    const startDate = ref(null);
    const endDate = ref(null);


    let chart = null;

    const updateSensorOptions = () => {
      if (!selectedLocation.value || !locationSensorMap.value[selectedLocation.value]) {
        indoorSensorOptions.value = [];
        outdoorSensorOptions.value = [];
        return;
      }

      indoorSensorOptions.value = locationSensorMap.value[selectedLocation.value].indoor || [];
      outdoorSensorOptions.value = locationSensorMap.value[selectedLocation.value].outdoor || [];

      // Special case for "East Point"
      if (selectedLocation.value === 'East Point') {
        selectedIndoorSensor.value = indoorSensorOptions.value[0] || 'None';
        selectedOutdoorSensor.value = outdoorSensorOptions.value[0] || 'None';
        showDelta.value = false; // Disable delta for "East Point"
      } else {
        // Reset default behavior for other locations
        if (!indoorSensorOptions.value.includes(selectedIndoorSensor.value) && selectedIndoorSensor.value !== 'None') {
          selectedIndoorSensor.value = 'None';
        }
        if (!outdoorSensorOptions.value.includes(selectedOutdoorSensor.value) && selectedOutdoorSensor.value !== 'None') {
          selectedOutdoorSensor.value = 'None';
        }
        showDelta.value = true; // Enable delta for other locations by default
      }
    };

    const initChart = () => {
      chart = echarts.init(document.getElementById('chart'));
      const option = {
        title: {
          text: 'Sensor Data',
        },
        tooltip: {
          trigger: 'axis',
        },
        xAxis: {
          type: 'category',
          data: [],
          name: 'Time (UTC)',
          nameLocation: 'center',
          nameTextStyle: {
            padding: [35, 0, 0, 0],
          },
        },
        yAxis: {
          type: 'value',
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: 80,
          containLabel: true,
        },
        dataZoom: [
          {
            type: 'inside',
          },
          {
            type: 'slider',
            bottom: 40,
          },
        ],
        series: [],
      };
      chart.setOption(option);
    };

    const fetchData = async () => {
      if (!selectedLocation.value) {
        return;
      }

      if (!startDate.value || !endDate.value) {
        console.warn('Start and end dates are required.');
        return;
      }
      if (new Date(startDate.value) > new Date(endDate.value)) {
        console.warn('Start date cannot be after end date.');
        return;
      }

      let timestamps = null;
      const series = [];

      const loc = selectedLocation.value;
      const sensorType = selectedSensor.value;
      // const rangeStr = `${selectedRangeDays.value}d`;
      // Format dates to ISO string
      const startDateISO = new Date(startDate.value).toISOString();
      const endDateISO = new Date(endDate.value).toISOString();

      console.log(`Fetching data for location: ${loc}, sensorType: ${sensorType}, startDate: ${startDateISO}, endDate: ${endDateISO}`);

      console.log("Show Delta: ", showDelta.value);
      // If delta is shown, we call the delta endpoint:
      if (showDelta.value) {
        console.log("showDelta is true");
        // For delta endpoint, we need indoor/outdoor sensor names
        const defaultIndoor = indoorSensorOptions.value[0];
        const defaultOutdoor = outdoorSensorOptions.value[0];

        if (!defaultIndoor || !defaultOutdoor) {
          console.error('No sensors available to compute delta for this location.');
          return;
        }

        const indoorParam = selectedIndoorSensor.value === 'None' ? defaultIndoor : selectedIndoorSensor.value;
        const outdoorParam = selectedOutdoorSensor.value === 'None' ? defaultOutdoor : selectedOutdoorSensor.value;

        // const apiUrl = `/api/delta/${loc}/${sensorType}?indoor_sensor=${indoorParam}&outdoor_sensor=${outdoorParam}&range=${rangeStr}`;
        const apiUrl = `/api/delta/${loc}/${sensorType}?indoor_sensor=${indoorParam}&outdoor_sensor=${outdoorParam}&start_date=${startDateISO}&end_date=${endDateISO}`;
        console.log("API URL:", apiUrl);
        try {
          console.log("indoor try");
          const response = await apiClient.get(apiUrl);
          console.log("Delta API Response:", response.data);
          const { timestamps: newTimestamps, indoor_value, outdoor_value, values: delta_values } = response.data;
          timestamps = newTimestamps;

          // Show indoor line if user selected a sensor
          if (selectedIndoorSensor.value !== 'None') {
            series.push({
              name: `${sensorType} indoor`,
              type: 'line',
              data: indoor_value,
              smooth: true,
            });
          }

          // Show outdoor line if user selected a sensor
          if (selectedOutdoorSensor.value !== 'None') {
            series.push({
              name: `${sensorType} outdoor`,
              type: 'line',
              data: outdoor_value,
              smooth: true,
            });
          }

          // Always show delta line
          series.push({
            name: `${sensorType} delta`,
            type: 'line',
            data: delta_values,
            smooth: true,
          });
        } catch (error) {
          console.error('Error fetching delta data:', error);
        }
      } else {
        // Delta not shown, so we only show raw indoor/outdoor data if selected
        if (selectedIndoorSensor.value !== 'None') {
          // const indoorUrl = `/api/data/${loc}/${sensorType}/indoor/${selectedIndoorSensor.value}?range=${rangeStr}`;
          const indoorUrl = `/api/data/${loc}/${sensorType}/indoor/${selectedIndoorSensor.value}?start_date=${startDateISO}&end_date=${endDateISO}`;
          console.log("indoorURL: ", indoorUrl)
          try {
            const response = await apiClient.get(indoorUrl);
            console.log("Indoor API Response:", response.data);
            const { timestamps: indoorTimestamps, values: indoorValues } = response.data;
            if (!timestamps) {
              timestamps = indoorTimestamps;
            }
            series.push({
              name: `${sensorType} indoor`,
              type: 'line',
              data: indoorValues,
              smooth: true,
            });
          } catch (error) {
            console.error('Error fetching indoor data:', error);
          }
        }

        if (selectedOutdoorSensor.value !== 'None') {
          // const outdoorUrl = `/api/data/${loc}/${sensorType}/outdoor/${selectedOutdoorSensor.value}?range=${rangeStr}`;
          const outdoorUrl = `/api/data/${loc}/${sensorType}/outdoor/${selectedOutdoorSensor.value}?start_date=${startDateISO}&end_date=${endDateISO}`;
          console.log("Outdoor URL:", outdoorUrl);
          try {
            const response = await apiClient.get(outdoorUrl);
            console.log("Outdoor API Response:", response.data);
            const { timestamps: outdoorTimestamps, values: outdoorValues } = response.data;
            if (!timestamps) {
              timestamps = outdoorTimestamps;
            }
            series.push({
              name: `${sensorType} outdoor`,
              type: 'line',
              data: outdoorValues,
              smooth: true,
            });
          } catch (error) {
            console.error('Error fetching outdoor data:', error);
          }
        }
      }

      updateChart(timestamps, series);
    };

    // const updateChart = (timestamps, series) => {
    //   chart.clear();
    //   const option = {
    //     tooltip: {
    //       trigger: 'axis',
    //     },
    //     xAxis: {
    //       type: 'category',
    //       data: timestamps || [],
    //       name: 'Time (UTC)',
    //       nameLocation: 'center',
    //       nameTextStyle: {
    //         padding: [35, 0, 0, 0],
    //       },
    //     },
    //     yAxis: {
    //       type: 'value',
    //     },
    //     grid: {
    //       left: '3%',
    //       right: '4%',
    //       bottom: 80,
    //       containLabel: true,
    //     },
    //     dataZoom: [
    //       {
    //         type: 'inside',
    //       },
    //       {
    //         type: 'slider',
    //         bottom: 40,
    //       },
    //     ],
    //     series: series,
    //   };
    //   chart.setOption(option);
    // };

    const updateChart = (timestamps, series) => {
      if (!chart) {
        initChart(); // Initialize chart if it's not already initialized
      }

      const option = {
        title: {
          text: 'Sensor Data',
        },
        tooltip: {
          trigger: 'axis',
        },
        xAxis: {
          type: 'category',
          data: timestamps || [],
          name: 'Time (UTC)',
          nameLocation: 'center',
          nameTextStyle: {
            padding: [35, 0, 0, 0],
          },
        },
        yAxis: {
          type: 'value',
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: 80,
          containLabel: true,
        },
        dataZoom: [
          {
            type: 'inside',
          },
          {
            type: 'slider',
            bottom: 40,
          },
        ],
        series: series,
      };

      chart.setOption(option);
    };

    onMounted(async () => {
      // Fetch the location configuration from the JSON file
      try {
        const response = await axios.get('/locations.json');
        locationSensorMap.value = response.data;

        // Populate the locations list
        locations.value = Object.keys(locationSensorMap.value);

        // Set a default selected location if not set
        if (!selectedLocation.value) {
          selectedLocation.value = locations.value[0];
        }

        updateSensorOptions();
        initChart();
        fetchData();
      } catch (error) {
        console.error('Error fetching location data:', error);
      }
    });

    const updateSensorsFromParent = (location, indoor, outdoor) => {
      selectedLocation.value = location;
      selectedIndoorSensor.value = indoor;
      selectedOutdoorSensor.value = outdoor;
      updateSensorOptions();
      fetchData();
    };

    return {
      locations,
      sensors,
      indoorSensorOptions,
      outdoorSensorOptions,
      selectedLocation,
      selectedSensor,
      selectedIndoorSensor,
      selectedOutdoorSensor,
      showDelta,
      // possibleRanges,
      // selectedRangeDays,
      startDate,
      endDate,
      updateSensorOptions,
      fetchData,
      updateSensorsFromParent
    };
  },
};
</script>

<style scoped>
.container {
  padding: 20px;
}

.selectors {
  margin-bottom: 20px;
}

select {
  margin-right: 10px;
}
</style>
