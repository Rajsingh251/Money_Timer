document.addEventListener('DOMContentLoaded', function () {
    const numberElement = document.getElementById('number');
    const remainingHoursElement = document.getElementById('remainingHours');
    const REDUCE_AMOUNT_PER_SECOND = 2.7; // Points deducted every second
    const TOTAL_DURATION_SECONDS = 8 * 60 * 60; // 8 hours in seconds

    let remainingTime = 0; // Points counter (can be negative)
    let elapsedSeconds = 0;
    let timerRunning = false; // Variable to track timer state

    document.getElementById('resetButton').addEventListener('click', resetTimer);
    document.getElementById('startStopButton').addEventListener('click', function () {
        if (timerRunning) {
            stopTimer();
        } else {
            startTimer();
        }
    });

    document.getElementById('addPointsButton').addEventListener('click', function () {
        const pointsToAdd = prompt('Enter the number of points to add:');
        if (pointsToAdd !== null && !isNaN(pointsToAdd)) {
            addPoints(parseFloat(pointsToAdd));
        } else {
            alert('Please enter a valid number.');
        }
    });

    function updateTimersFromAPI() {
        fetch('http://localhost:8000/points_info')
            .then(response => response.json())
            .then(data => {
                remainingTime = parseFloat(data.points);
                elapsedSeconds = data.elapsed_seconds;
                updateNumber();
                updateRemainingHours();
                timerRunning = data.timer_running;
                updateStartStopButton();
            })
            .catch(error => {
                console.error('Error fetching timer status:', error);
            });
    }

    function formatRemainingTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
    }

    function updateNumber() {
        numberElement.textContent = remainingTime.toFixed(2);
        if (remainingTime >= 0) {
            numberElement.classList.add('positive');
            numberElement.classList.remove('negative');
        } else {
            numberElement.classList.remove('positive');
            numberElement.classList.add('negative');
        }
    }

    function updateRemainingHours() {
        const remainingSeconds = TOTAL_DURATION_SECONDS - elapsedSeconds;
        remainingHoursElement.textContent = `Remaining Hours: ${formatRemainingTime(remainingSeconds)}`;
    }

    function startTimer() {
        fetch('http://localhost:8000/start_timer', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(() => {
            timerRunning = true;
            updateStartStopButton();
        })
        .catch(error => {
            console.error('Error starting timer:', error);
        });
    }

    function stopTimer() {
        fetch('http://localhost:8000/stop_timer', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(() => {
            timerRunning = false;
            updateStartStopButton();
        })
        .catch(error => {
            console.error('Error stopping timer:', error);
        });
    }

    function resetTimer() {
        fetch('http://localhost:8000/reset_timer', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(() => {
            remainingTime = 0;
            elapsedSeconds = 0;
            updateNumber();
            updateRemainingHours();
            timerRunning = false;
            updateStartStopButton();
        })
        .catch(error => {
            console.error('Error resetting timer:', error);
        });
    }

    function addPoints(amount) {
        fetch('http://localhost:8000/add_points', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ points: amount })
        })
        .then(response => response.json())
        .then(data => {
            remainingTime = parseFloat(data.points);
            updateNumber();
        })
        .catch(error => {
            console.error('Error adding points:', error);
        });
    }

    function updateStartStopButton() {
        const button = document.getElementById('startStopButton');
        button.textContent = timerRunning ? 'Stop Timer' : 'Start Timer';
    }

    // Fetch data and update every second
    setInterval(updateTimersFromAPI, 500);

    // Initial call to fetch data
    updateTimersFromAPI();
});