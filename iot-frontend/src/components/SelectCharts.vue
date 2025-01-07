<template>
  <!-- Overall Chart Container -->
  <div class="container"> 
      <!-- Left Sidebar -->
      <div class="sidebar">
          <h3 class="text-md font-semibold text-center p-4">Sensor Controls</h3>
          <div>
          <!-- Location Selection -->
              <div class="selectors">
                  <label for="location-select" class="text-sm font-medium">
                      Location
                  </label>
                  <select
                      id="location-select"
                      v-model="selectedLocation"
                      @change="() => { updateSensorOptions(); fetchData(); }"
                      class="w-full rounded-md border border-gray-300 p-2 text-sm focus:ring-2 focus:ring-blue-500"
                      >  
                      <option v-for="location in locations" :key="location" :value="location">
                      {{ location }}
                      </option>
                  </select>
              </div>

              <!-- Sensor Type -->
              <div class="selectors">
                  <label class="block text-sm font-medium">
                      Sensor Type
                  </label>
                  <select
                      v-model="selectedSensor"
                      @change="fetchData"
                      class="w-full rounded-md border border-gray-300 p-2 text-sm focus:ring-2 focus:ring-blue-500"
                  >
                      <option v-for="sensor in sensors" :key="sensor" :value="sensor">
                          {{ sensor.charAt(0).toUpperCase() + sensor.slice(1) }}
                      </option>
                  </select>
              </div>

              <!-- Indoor Sensor -->
              <div class="selectors">
                  <label class="block text-sm font-medium text-gray-700">
                      Indoor Sensor
                  </label>
                  <select
                      v-model="selectedIndoorSensor"
                      @change="fetchData"
                      class="w-full rounded-md border border-gray-300 p-2 text-sm focus:ring-2 focus:ring-blue-500"
                      >
                      <option value="None">None</option>
                      <option v-for="sensor in indoorSensorOptions" :key="sensor" :value="sensor">
                          {{ sensor }}
                      </option>
                  </select>
              </div>

              <!-- Outdoor Sensor -->
              <div class="selectors">
                  <label class="block text-sm font-medium text-gray-700">
                      Outdoor Sensor
                  </label>
                  <select
                      v-model="selectedOutdoorSensor"
                      @change="fetchData"
                      class="w-full rounded-md border border-gray-300 p-2 text-sm focus:ring-2 focus:ring-blue-500"
                  >
                      <option value="None">None</option>
                      <option v-for="sensor in outdoorSensorOptions" :key="sensor" :value="sensor">
                          {{ sensor }}
                      </option>
                  </select>
              </div>

              <!-- Time Range -->
              <div class="selectors">
                  <label class="block text-sm font-medium text-gray-700">
                      Time Range
                  </label>
                  <select
                      v-model="selectedRangeDays"
                      @change="fetchData"
                      class="w-full rounded-md border border-gray-300 p-2 text-sm focus:ring-2 focus:ring-blue-500"
                  >
                      <option v-for="days in possibleRanges" :key="days" :value="days">
                          {{ days }} {{ days === 1 ? 'day' : 'days' }}
                      </option>
                  </select>
              </div>

              <!-- Delta Checkbox -->
              <div class="text-center">
                  <label class="flex items-center space-x-2 cursor-pointer">
                      <input
                      type="checkbox"
                      v-model="showDelta"
                      @change="fetchData"
                      class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
                      >
                      <span class="text-sm font-medium text-gray-700">Show Delta</span>
                  </label>
              </div>
          </div>
      </div>

      <!-- Main Content Area -->
      <div class="main-chart relative">
          <div ref="chartContainer" id="chart2"  style="width: 100%; height: 300px;"></div>
      </div>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue';
import * as echarts from 'echarts';
import axios from 'axios';

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

    // Time range selection
    const possibleRanges = ref([1, 3, 7, 14, 30]);
    const selectedRangeDays = ref(7); // default 7 days

    // Loading
    const isLoading = ref(false);

    let chart = null;

    watch(isLoading, (newValue) => {
      if (newValue) {
          document.body.style.cursor = 'wait';  
      } else {
          document.body.style.cursor = 'default'; 
      }
    });

    const updateSensorOptions = () => {
      if (!selectedLocation.value || !locationSensorMap.value[selectedLocation.value]) {
        indoorSensorOptions.value = [];
        outdoorSensorOptions.value = [];
        return;
      }

      indoorSensorOptions.value = locationSensorMap.value[selectedLocation.value].indoor || [];
      outdoorSensorOptions.value = locationSensorMap.value[selectedLocation.value].outdoor || [];

      // Reset selected sensors if they're no longer in the options
      if (!indoorSensorOptions.value.includes(selectedIndoorSensor.value) && selectedIndoorSensor.value !== 'None') {
        selectedIndoorSensor.value = 'None';
      }
      if (!outdoorSensorOptions.value.includes(selectedOutdoorSensor.value) && selectedOutdoorSensor.value !== 'None') {
        selectedOutdoorSensor.value = 'None';
      }
    };

    const initChart = () => {
      chart = echarts.init(document.getElementById('chart2'));
      const option = {
        title: {
          text: 'Sensor Data',
        },
        tooltip: {
          trigger: 'axis',
        },
        legend: {
          data: [],
          top: 'bottom',
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

      //console.log('Setting isLoading to true'); // Debugging
      isLoading.value = true;

      let timestamps = null;
      const series = [];

      const loc = selectedLocation.value;
      const sensorType = selectedSensor.value;
      const rangeStr = `${selectedRangeDays.value}d`;

      // If delta is shown, we call the delta endpoint:
      if (showDelta.value) {
        // For delta endpoint, we need indoor/outdoor sensor names
        const defaultIndoor = indoorSensorOptions.value[0];
        const defaultOutdoor = outdoorSensorOptions.value[0];

        if (!defaultIndoor || !defaultOutdoor) {
          console.error('No sensors available to compute delta for this location.');
          return;
        }

        const indoorParam = selectedIndoorSensor.value === 'None' ? defaultIndoor : selectedIndoorSensor.value;
        const outdoorParam = selectedOutdoorSensor.value === 'None' ? defaultOutdoor : selectedOutdoorSensor.value;

        const apiUrl = `/api/delta/${loc}/${sensorType}?indoor_sensor=${indoorParam}&outdoor_sensor=${outdoorParam}&range=${rangeStr}`;
        try {
          
          //console.log("Starting Fetch")
          const response = await axios.get(apiUrl);
          //console.log('Fetch success:', response.data);
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
          // console.error('Error fetching delta data:', error);
        } finally {
          // console.log('Setting isLoading to false 1')
          isLoading.value = false;
        }
      } else {
        // Delta not shown, so we only show raw indoor/outdoor data if selected
        if (selectedIndoorSensor.value !== 'None') {
          const indoorUrl = `/api/data/${loc}/${sensorType}/indoor/${selectedIndoorSensor.value}?range=${rangeStr}`;
          try {
            const response = await axios.get(indoorUrl);
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
          const outdoorUrl = `/api/data/${loc}/${sensorType}/outdoor/${selectedOutdoorSensor.value}?range=${rangeStr}`;
          try {
            const response = await axios.get(outdoorUrl);
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
          //   console.error('Error fetching outdoor data:', error);
          } finally {
              // console.log('Setting isLoading to false'); // Debugging
              isLoading.value = false;
          }
        }
      }

      updateChart(timestamps, series);
    };

    const updateChart = (timestamps, series) => {
      chart.clear();
      const legendData = series.map((item) => item.name); // Extract names for legend

      const option = {
        tooltip: {
          trigger: 'axis',
        },
        legend: {
          data: legendData, // Use series names for legend
          top: 'bottom',
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
      possibleRanges,
      selectedRangeDays,
      updateSensorOptions,
      fetchData,
      updateSensorsFromParent,
      isLoading
    };
  },
};
</script>

<style scoped>
.container {
  display: flex;
  padding: 20px;
  background: #ffffff;
  border-radius: 1% / 5%;
}
.selectors {
  margin-bottom: 10%;
  margin-right: 1%;
  text-align: left;
}
.sidebar {
  position: relative;
  top: 0px;
  width: 20%;
  border-right: 0px solid #514d4d;  /* Slate 300 equivalent */
  padding: 1px;
}
.main-chart {
  position: relative;
  width: 80%;
  border: 2px solid #514d4d;
  align-items: start;
  margin-left: auto;
  margin-right: 0;
  padding: 20px;
}
select {
  margin-right: 10px;
}

</style>