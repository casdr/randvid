// Config variables: change them to point to your own servers
const SIGNALING_SERVER_URL = '/';
const TURN_SERVER_URL = 'dev4-lux1.raaw.eu:3478';
const TURN_SERVER_USERNAME = 'casdr';
const TURN_SERVER_CREDENTIAL = 'Oochah6sheiF';

const PC_CONFIG = {
  iceServers: [
    {
      urls: 'turn:' + TURN_SERVER_URL + '?transport=tcp',
      username: TURN_SERVER_USERNAME,
      credential: TURN_SERVER_CREDENTIAL
    },
    {
      urls: 'turn:' + TURN_SERVER_URL + '?transport=udp',
      username: TURN_SERVER_USERNAME,
      credential: TURN_SERVER_CREDENTIAL
    }
  ]
};

let socket = io(SIGNALING_SERVER_URL, { autoConnect: false });

let countdownSeconds = 0;

socket.on('data', (data) => {
  console.log('Data received: ', data);
  handleSignalingData(data);
});

socket.on('ready', () => {
  console.log('Ready');
  createPeerConnection();
  sendOffer();
});

socket.emit('join_wait', { 'name': 'Cas' });


let sendData = (data) => {
  socket.emit('data', data);
};

let pc;
let localStream;
let remoteStreamElement = document.querySelector('#remoteStream');


let getLocalStream = () => {
  displayMuteButton()
  navigator.mediaDevices.getUserMedia({ audio: true, video: true })
    .then((stream) => {
      console.log('Stream found');
      const localVid = document.getElementById('localStream');
      localStream = stream; socket.connect();
      localVid.muted = true;
      localVid.srcObject = localStream;
    })
    .catch(error => {
      console.error('Stream not found: ', error);
    });
}

let createPeerConnection = () => {
  try {
    pc = new RTCPeerConnection(PC_CONFIG);
    pc.onicecandidate = onIceCandidate;
    pc.onaddstream = onAddStream;
    pc.addStream(localStream);
    console.log('PeerConnection created');
  } catch (error) {
    console.error('PeerConnection failed: ', error);
  }
};

let sendOffer = () => {
  console.log('Send offer');
  setTimeout(function () {
    pc.createOffer().then(
      setAndSendLocalDescription,
      (error) => { console.error('Send offer failed: ', error); }
    );
  }, 500);
};

let sendAnswer = () => {
  console.log('Send answer');
  pc.createAnswer().then(
    setAndSendLocalDescription,
    (error) => { console.error('Send answer failed: ', error); }
  );
};

let setAndSendLocalDescription = (sessionDescription) => {
  pc.setLocalDescription(sessionDescription);
  console.log('Local description set');
  sendData(sessionDescription);
};

let onIceCandidate = (event) => {
  if (event.candidate) {
    console.log('ICE candidate');
    sendData({
      type: 'candidate',
      candidate: event.candidate
    });
  }
};

let onAddStream = (event) => {
  console.log('Add stream');
  remoteStreamElement.srcObject = event.stream;
  displayMuteButton()
};

let handleSignalingData = (data) => {
  switch (data.type) {
    case 'offer':
      createPeerConnection();
      pc.setRemoteDescription(new RTCSessionDescription(data));
      sendAnswer();
      break;
    case 'answer':
      pc.setRemoteDescription(new RTCSessionDescription(data));
      break;
    case 'candidate':
      pc.addIceCandidate(new RTCIceCandidate(data.candidate));
      break;
    case 'disconnect':
      if (pc) {
        pc.close();
      }
      break;
  }
};

// Start connection
getLocalStream();

document.getElementById('muteLocal').onclick = function () {
  localStream.getAudioTracks()[0].enabled = !(localStream.getAudioTracks()[0].enabled);
  if (localStream.getAudioTracks()[0].enabled) {
    document.getElementById('muteLocal').innerHTML = "Mute"
  } else {
    document.getElementById('muteLocal').innerHTML = "Unmute"
  }
}

document.getElementById('muteRemote').onclick = function () {
  pc.getRemoteStreams()[0].getAudioTracks()[0].enabled = !(pc.getRemoteStreams()[0].getAudioTracks()[0].enabled);
  if (pc.getRemoteStreams()[0].getAudioTracks()[0].enabled) {
    document.getElementById('muteRemote').innerHTML = "Mute"
  } else {
    document.getElementById('muteRemote').innerHTML = "Unmute"
  }
}



document.getElementById('turnOffCam').onclick = function () {
  localStream.getVideoTracks()[0].enabled = !(localStream.getVideoTracks()[0].enabled);
  if (localStream.getVideoTracks()[0].enabled) {
    document.getElementById('turnOffCam').innerHTML = "Turn off camera"
  } else {
    document.getElementById('turnOffCam').innerHTML = "Turn on camera"
  }
}

socket.on('next_round', function (seconds) {
  countdownSeconds = parseInt(seconds);
});

socket.on('remote_name', function (name) {
  document.getElementById('name').innerHTML = name
});

setInterval(function () {
  countdownSeconds--;
  if (countdownSeconds < 0) {
    countdownSeconds = 0;
  }
  document.getElementById('countdown').innerHTML = countdownSeconds
}, 1000);

function displayMuteButton() {
  if (remoteStreamElement.srcObject == null) {
    document.getElementById("muteRemote").style.visibility = "hidden";
  } else {
    document.getElementById("muteRemote").style.visibility = "visible";
    
  }
}