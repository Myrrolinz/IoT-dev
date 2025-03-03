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

      <!-- Show all interpolated points checkbox -->
      <div v-if="showDelta">
        <input type="checkbox" id="show-all-interpolated" v-model="showAllInterpolated" @change="fetchData" />
        <label for="show-all-interpolated">Show All Interpolated Points</label>
      </div>

      <!-- Gap period threshold selection -->
      <div v-if="showDelta">
        <label for="gap-threshold">Big Gap Threshold (minutes):</label>
        <select id="gap-threshold" v-model="gapThreshold" @change="fetchData">
          <option v-for="threshold in gapThresholdOptions" :key="threshold" :value="threshold">
            {{ threshold }}
          </option>
        </select>
      </div>

      <!-- Range selection -->
      <label for="range-select">Time Range (days):</label>
      <select id="range-select" v-model="selectedRangeDays" @change="fetchData">
        <option v-for="d in possibleRanges" :key="d" :value="d">{{ d }} days</option>
      </select>
    </div>

    <!-- Display gap warning if present -->
    <div v-if="gapWarning" class="warning">{{ gapWarning }}</div>

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
    const locationSensorMap = ref({});
    const locations = ref([]);
    const sensors = ref(['co2', 'humidity', 'temperature', 'pressure']);
    const indoorSensorOptions = ref([]);
    const outdoorSensorOptions = ref([]);
    const selectedLocation = ref(props.initialLocation);
    const selectedSensor = ref('co2');
    const selectedIndoorSensor = ref(props.initialIndoorSensor);
    const selectedOutdoorSensor = ref(props.initialOutdoorSensor);
    const showDelta = ref(true);
    const showAllInterpolated = ref(false); // New state for toggling all interpolated points
    const possibleRanges = ref([1, 3, 7, 14, 30, 60]);
    const selectedRangeDays = ref(7);
    const gapWarning = ref('');
    const gapThreshold = ref(30); // New state for gap threshold, default 30 minutes
    const gapThresholdOptions = ref([10, 20, 30, 60, 120, 240]); // Options for gap threshold
    const largeGapThreshold = ref(1440); // New state for large gap threshold, default 1 day (1440 minutes)

    let chart = null;

    const updateSensorOptions = () => {
      if (!selectedLocation.value || !locationSensorMap.value[selectedLocation.value]) {
        indoorSensorOptions.value = [];
        outdoorSensorOptions.value = [];
        return;
      }

      indoorSensorOptions.value = locationSensorMap.value[selectedLocation.value].indoor || [];
      outdoorSensorOptions.value = locationSensorMap.value[selectedLocation.value].outdoor || [];

      if (selectedLocation.value === 'East Point') {
        selectedIndoorSensor.value = indoorSensorOptions.value[0] || 'None';
        selectedOutdoorSensor.value = outdoorSensorOptions.value[0] || 'None';
        showDelta.value = false;
      } else {
        if (!indoorSensorOptions.value.includes(selectedIndoorSensor.value) && selectedIndoorSensor.value !== 'None') {
          selectedIndoorSensor.value = 'None';
        }
        if (!outdoorSensorOptions.value.includes(selectedOutdoorSensor.value) && selectedOutdoorSensor.value !== 'None') {
          selectedOutdoorSensor.value = 'None';
        }
        showDelta.value = true;
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

      let timestamps = null;
      let isInterpolatedIndoor = null;
      let isInterpolatedOutdoor = null;
      let gapMetadata = null;
      const series = [];
      gapWarning.value = '';

      const loc = selectedLocation.value;
      const sensorType = selectedSensor.value;
      const rangeStr = `${selectedRangeDays.value}d`;

      if (showDelta.value) {
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
          const response = await apiClient.get(apiUrl);
          const { timestamps: newTimestamps, indoor_value, outdoor_value, values: delta_values, gap_metadata, is_interpolated_indoor, is_interpolated_outdoor } = response.data;
          timestamps = newTimestamps;
          isInterpolatedIndoor = is_interpolated_indoor;
          isInterpolatedOutdoor = is_interpolated_outdoor;
          gapMetadata = gap_metadata;

          // Debugging: Verify lengths
          console.log('Timestamps length:', timestamps.length);
          console.log('Indoor values length:', indoor_value.length);
          console.log('Outdoor values length:', outdoor_value.length);
          console.log('Delta values length:', delta_values.length);
          console.log('isInterpolatedIndoor length:', isInterpolatedIndoor.length);
          console.log('isInterpolatedOutdoor length:', isInterpolatedOutdoor.length);

          // Handle gap metadata
          if (gap_metadata && gap_metadata.gap_percentage > 10) {
            gapWarning.value = `Warning: ${gap_metadata.gap_percentage.toFixed(2)}% of the data is interpolated due to gaps.`;
          }

          if (selectedIndoorSensor.value !== 'None') {
            series.push({
              name: `${sensorType} indoor`,
              type: 'line',
              data: indoor_value,
              smooth: true,
            });
          }

          if (selectedOutdoorSensor.value !== 'None') {
            series.push({
              name: `${sensorType} outdoor`,
              type: 'line',
              data: outdoor_value,
              smooth: true,
            });
          }

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
        if (selectedIndoorSensor.value !== 'None') {
          const indoorUrl = `/api/data/${loc}/${sensorType}/indoor/${selectedIndoorSensor.value}?range=${rangeStr}`;
          try {
            const response = await apiClient.get(indoorUrl);
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
            const response = await apiClient.get(outdoorUrl);
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

      updateChart(timestamps, series, isInterpolatedIndoor, isInterpolatedOutdoor, gapMetadata);
    };

    const updateChart = (timestamps, series, isInterpolatedIndoor, isInterpolatedOutdoor, gapMetadata) => {
      chart.clear();

      // Function to determine if a timestamp is within a "big" gap period
      const isInBigGap = (timestamp, gapPeriods, thresholdMinutes) => {
        return gapPeriods.some(period => {
          const start = new Date(period.start).getTime();
          const end = new Date(period.end).getTime();
          const ts = new Date(timestamp).getTime();
          return ts >= start && ts <= end && period.duration_minutes >= thresholdMinutes;
        });
      };

      // Enhance series to visually indicate gaps using markers and break lines for large gaps
      const modifiedSeries = series.map(s => {
        if (s.name.includes('indoor') && isInterpolatedIndoor && gapMetadata) {
          const indoorGapPeriods = gapMetadata.indoor_gap_periods || [];
          const dataWithStyles = s.data.map((value, index) => {
            const timestamp = timestamps[index];
            const isBigGap = isInBigGap(timestamp, indoorGapPeriods, gapThreshold.value);
            const isLargeGap = isInBigGap(timestamp, indoorGapPeriods, largeGapThreshold.value);
            const isInterpolated = isInterpolatedIndoor[index];
            const showMarker = isBigGap || (showAllInterpolated.value && isInterpolated);
            return {
              value: isLargeGap ? null : value, // Break the line for large gaps
              symbol: showMarker ? 'circle' : 'none',
              symbolSize: showMarker ? 6 : 0,
              itemStyle: showMarker ? { color: 'red' } : {}
            };
          });
          return { ...s, data: dataWithStyles, connectNulls: false }; // Ensure lines are broken at null values
        } else if (s.name.includes('outdoor') && isInterpolatedOutdoor && gapMetadata) {
          const outdoorGapPeriods = gapMetadata.outdoor_gap_periods || [];
          const dataWithStyles = s.data.map((value, index) => {
            const timestamp = timestamps[index];
            const isBigGap = isInBigGap(timestamp, outdoorGapPeriods, gapThreshold.value);
            const isLargeGap = isInBigGap(timestamp, outdoorGapPeriods, largeGapThreshold.value);
            const isInterpolated = isInterpolatedOutdoor[index];
            const showMarker = isBigGap || (showAllInterpolated.value && isInterpolated);
            return {
              value: isLargeGap ? null : value, // Break the line for large gaps
              symbol: showMarker ? 'circle' : 'none',
              symbolSize: showMarker ? 6 : 0,
              itemStyle: showMarker ? { color: 'red' } : {}
            };
          });
          return { ...s, data: dataWithStyles, connectNulls: false }; // Ensure lines are broken at null values
        } else if (s.name.includes('delta') && isInterpolatedIndoor && isInterpolatedOutdoor && gapMetadata) {
          const indoorGapPeriods = gapMetadata.indoor_gap_periods || [];
          const outdoorGapPeriods = gapMetadata.outdoor_gap_periods || [];
          const dataWithStyles = s.data.map((value, index) => {
            const timestamp = timestamps[index];
            const isBigGapIndoor = isInBigGap(timestamp, indoorGapPeriods, gapThreshold.value);
            const isBigGapOutdoor = isInBigGap(timestamp, outdoorGapPeriods, gapThreshold.value);
            const isLargeGapIndoor = isInBigGap(timestamp, indoorGapPeriods, largeGapThreshold.value);
            const isLargeGapOutdoor = isInBigGap(timestamp, outdoorGapPeriods, largeGapThreshold.value);
            const isInterpolated = isInterpolatedIndoor[index] || isInterpolatedOutdoor[index];
            const isBigGap = isBigGapIndoor || isBigGapOutdoor;
            const isLargeGap = isLargeGapIndoor || isLargeGapOutdoor;
            const showMarker = isBigGap || (showAllInterpolated.value && isInterpolated);
            return {
              value: isLargeGap ? null : value, // Break the line for large gaps
              symbol: showMarker ? 'circle' : 'none',
              symbolSize: showMarker ? 6 : 0,
              itemStyle: showMarker ? { color: 'red' } : {}
            };
          });
          return { ...s, data: dataWithStyles, connectNulls: false }; // Ensure lines are broken at null values
        }
        return s;
      });

      // Add shaded regions for gap periods, with stronger shading for large gaps
      const markAreas = [];
      if (gapMetadata) {
        const indoorGapPeriods = gapMetadata.indoor_gap_periods || [];
        const outdoorGapPeriods = gapMetadata.outdoor_gap_periods || [];
        const allGapPeriods = [...indoorGapPeriods, ...outdoorGapPeriods];

        allGapPeriods.forEach(period => {
          const isLargeGap = period.duration_minutes >= largeGapThreshold.value;
          markAreas.push({
            name: isLargeGap ? 'Large Gap' : 'Gap Period',
            xAxis: period.start,
            itemStyle: { color: isLargeGap ? 'rgba(255, 0, 0, 0.3)' : 'rgba(255, 0, 0, 0.1)' } // Stronger shading for large gaps
          }, {
            xAxis: period.end
          });
        });
      }

      const option = {
        tooltip: {
          trigger: 'axis',
          formatter: (params) => {
            const index = params[0].dataIndex;
            let tooltipText = `${params[0].axisValueLabel}<br />`;
            params.forEach(p => {
              let interpolationStatus = '';
              if (p.seriesName.includes('indoor') && isInterpolatedIndoor && isInterpolatedIndoor[index]) {
                interpolationStatus = ' (Indoor Interpolated)';
              } else if (p.seriesName.includes('outdoor') && isInterpolatedOutdoor && isInterpolatedOutdoor[index]) {
                interpolationStatus = ' (Outdoor Interpolated)';
              } else if (p.seriesName.includes('delta')) {
                if (isInterpolatedIndoor && isInterpolatedIndoor[index] && isInterpolatedOutdoor && isInterpolatedOutdoor[index]) {
                  interpolationStatus = ' (Both Interpolated)';
                } else if (isInterpolatedIndoor && isInterpolatedIndoor[index]) {
                  interpolationStatus = ' (Indoor Interpolated)';
                } else if (isInterpolatedOutdoor && isInterpolatedOutdoor[index]) {
                  interpolationStatus = ' (Outdoor Interpolated)';
                }
              }
              tooltipText += `${p.seriesName}: ${p.value !== null ? p.value : 'N/A'}${interpolationStatus}<br />`;
            });
            return tooltipText;
          },
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
        series: modifiedSeries,
        markArea: {
          data: markAreas
        }
      };

      console.log('Chart options:', option); // Debugging: Log chart options
      chart.setOption(option);
    };

    onMounted(async () => {
      try {
        const response = await axios.get('/locations.json');
        locationSensorMap.value = response.data;
        locations.value = Object.keys(locationSensorMap.value);

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
      showAllInterpolated, // Expose new state to template
      possibleRanges,
      selectedRangeDays,
      gapWarning,
      gapThreshold, // Expose new state to template
      gapThresholdOptions, // Expose gap threshold options to template
      largeGapThreshold, // Expose new state for large gap threshold
      updateSensorOptions,
      fetchData,
      updateSensorsFromParent
    };
  },
};
</script>

<style scoped>
/* Conteneur principal */
.container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  background: linear-gradient(135deg, #f9f9f9, #e9ecef);
  /* Dégradé subtil pour un fond dynamique */
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  /* Ombre plus prononcée pour un effet de profondeur */
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  /* Animation au survol */
}

.container:hover {
  transform: translateY(-5px);
  /* Léger soulèvement au survol */
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
  /* Ombre renforcée */
}

/* Titre */
h1 {
  font-size: 32px;
  font-weight: 700;
  color: #2c3e50;
  /* Couleur sombre et élégante */
  margin-bottom: 30px;
  text-align: center;
  text-transform: uppercase;
  /* Majuscules pour un look professionnel */
  letter-spacing: 1px;
  /* Espacement des lettres pour une meilleure lisibilité */
  position: relative;
}

h1::after {
  content: '';
  display: block;
  width: 50px;
  height: 3px;
  background: #007bff;
  /* Ligne décorative sous le titre */
  margin: 10px auto 0;
  border-radius: 2px;
}

/* Conteneur des sélecteurs */
.selectors {
  margin-bottom: 30px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  /* Grille responsive avec colonnes plus larges */
  gap: 25px;
  /* Espacement accru pour une meilleure séparation */
  align-items: center;
  padding: 15px;
  background: #fff;
  /* Fond blanc pour les sélecteurs */
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  /* Ombre légère pour un effet de carte */
}

/* Style des labels */
label {
  font-size: 14px;
  font-weight: 600;
  color: #34495e;
  /* Couleur sombre et élégante */
  margin-right: 10px;
  display: flex;
  align-items: center;
  gap: 5px;
  /* Espacement entre l'icône et le texte (si icônes ajoutées) */
}

/* Style des sélecteurs (dropdowns) */
select {
  padding: 10px 15px;
  font-size: 14px;
  border: 1px solid #dfe6e9;
  border-radius: 8px;
  background-color: #fff;
  color: #2c3e50;
  cursor: pointer;
  transition: all 0.3s ease;
  /* Transition fluide pour toutes les propriétés */
  appearance: none;
  /* Supprime le style natif du navigateur */
  background-image: url('data:image/svg+xml;utf8,<svg fill="none" stroke="%2334495e" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"></path></svg>');
  /* Flèche personnalisée */
  background-repeat: no-repeat;
  background-position: right 10px center;
  background-size: 16px;
}

select:hover,
select:focus {
  border-color: #007bff;
  /* Couleur de survol/focus */
  box-shadow: 0 0 8px rgba(0, 123, 255, 0.3);
  /* Ombre plus prononcée au focus */
  outline: none;
}

/* Style des checkboxes */
input[type="checkbox"] {
  margin-right: 8px;
  cursor: pointer;
  width: 18px;
  height: 18px;
  accent-color: #007bff;
  /* Couleur personnalisée pour la checkbox */
  transition: transform 0.2s ease;
  /* Animation au clic */
}

input[type="checkbox"]:hover {
  transform: scale(1.1);
  /* Agrandissement léger au survol */
}

input[type="checkbox"]+label {
  font-size: 14px;
  color: #34495e;
  cursor: pointer;
  transition: color 0.3s ease;
  display: flex;
  align-items: center;
}

input[type="checkbox"]:hover+label,
input[type="checkbox"]:checked+label {
  color: #007bff;
  /* Couleur de survol ou sélection */
}

/* Style du message d'avertissement */
.warning {
  color: #e67e22;
  /* Orange pour les avertissements */
  background-color: #fff3e6;
  /* Fond clair pour les avertissements */
  padding: 12px 20px;
  border-radius: 8px;
  text-align: center;
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  /* Ombre légère */
  animation: fadeIn 0.5s ease-in-out;
  /* Animation d'apparition */
}

/* Style du conteneur du graphique */
#chart {
  width: 100%;
  height: 400px;
  background-color: #fff;
  /* Fond blanc pour le graphique */
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  /* Ombre plus prononcée */
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  /* Animation au survol */
}

#chart:hover {
  transform: translateY(-5px);
  /* Léger soulèvement au survol */
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
  /* Ombre renforcée */
}

/* Animation d'apparition */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Thème sombre */
@media (prefers-color-scheme: dark) {
  .container {
    background: linear-gradient(135deg, #1a1a1a, #2c3e50);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
  }

  h1 {
    color: #fff;
  }

  .selectors {
    background: #2c3e50;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
  }

  label {
    color: #ccc;
  }

  select {
    background-color: #34495e;
    color: #fff;
    border-color: #555;
    background-image: url('data:image/svg+xml;utf8,<svg fill="none" stroke="%23ccc" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"></path></svg>');
  }

  select:hover,
  select:focus {
    border-color: #007bff;
    box-shadow: 0 0 8px rgba(0, 123, 255, 0.5);
  }

  input[type="checkbox"]+label {
    color: #ccc;
  }

  input[type="checkbox"]:hover+label,
  input[type="checkbox"]:checked+label {
    color: #007bff;
  }

  .warning {
    color: #e67e22;
    background-color: #3e2723;
  }

  #chart {
    background-color: #2c3e50;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
  }
}

/* Responsivité */
@media (max-width: 768px) {
  .selectors {
    grid-template-columns: 1fr;
    /* Une seule colonne sur les petits écrans */
  }

  h1 {
    font-size: 24px;
  }

  select,
  label,
  input[type="checkbox"]+label {
    font-size: 13px;
  }

  .warning {
    font-size: 13px;
    padding: 8px 12px;
  }

  #chart {
    height: 300px;
    /* Réduction de la hauteur sur mobile */
  }
}
</style>