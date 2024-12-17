
var objectLists = {}
var network = [];
/**
	Function to initiate page to the state of the VPN.
	@param : bool : True if VPN is connected.
*/
function connectedVPN(connect) {
	vpnButton = document.getElementById("vpnButton");
	url = "/vpn?connect="+(connect?"false":"true");
	vpnButton.onclick = function () {
		waitImg = document.getElementById("waitImg");
		waitImg.style.display = "inline";
		vpnButton.style.display = "none";
		fetch(url, { method: 'GET' })
			.then(Result => Result.json())
			.then(retVal => {
				console.log('response :  '+retVal);
				connectedVPN(retVal.connected);
				waitImg.style.display = "none";
				vpnButton.style.display = "inline";
			})
			.catch(errorMsg => { console.log(errorMsg); }); 
	}
	vpnButton.innerHTML = connect?"Disconnect":"Connect";
	const vpnStatus = document.getElementById("vpnStatus");
	vpnStatus.innerHTML = connect?"up":"down";
}
function changeSthg() {
	// console.log("changeSthg()");
		document.getElementById("submitYamlParams")
			.src = "http://localhost:8000/img/save_32.ico";
}
function getNetwork() {
	val = document.getElementById('network.nodes').value.trim().replaceAll("'","\"");
	console.log("Network0:",val);
	network = JSON.parse(val);
	console.log("Network:",network);
}
function setNetwork() {
	console.log("setNetwork()");
	var nodes = document.getElementById("nodes").children;
	var networkById = {};
	// As id can be changed, search orginals ids
	for (n in network) {
		node = network[n]
		networkById[node.id] = node;
	}
	var refs = [networkById];
	for (i in nodes) {
		nodeElement = nodes[i];
		if (typeof nodeElement === 'object') {
			inputs = nodeElement.querySelectorAll('input');
			for (i in inputs) {
				input = inputs[i];
				if (typeof input === 'object') {
					ids = input.id.split('-');
					refs.length = 1;
					for (j=1; j<ids.length; j++) {
						refs[j] = refs[j-1][ids[j]];
					}
					if (refs[ids.length-1]!=input.value) {
						console.log(refs[ids.length-1] , " VS ", input.value);
						refs[ids.length-1] = input.value;
						for (j=ids.length-1; j>0; j--) {
							refs[j-1][ids[j]] = refs[j];
						}
					}
				}
			}
		}
	}
	myNetwork = [];
	for (i in refs[0]) {
		myNetwork.push(networkById[i]);
	}
	document.getElementById('network.nodes').value = JSON.stringify(myNetwork);
	console.log("setNetwork() => ", myNetwork);
	return true;
}
function deleteNode(index) {
	var node = document.getElementById("node-"+index);
	node.parentElement.removeChild(node);
	network2 = [];
	for (n in network) {
		node = network[n];
		if(node.id!=index) {
			network2.push(node);
		}
	}
	network = network2;
}
function getElement(index, attr, node, level=0) {
	// console.log("getElement(",index,", ",attr,", ",node,", ",level,")")
	var currentElement = document.createElement("div");
	if (level>0) {
		currentElement.classList.add("col-75");
	}
	currentElement.classList.add(index);
	attrId = attr.replaceAll("-","_")
	var myindex = index+"-"+attrId;
	if (node instanceof Array) {
		node = JSON.stringify(node);
	}
	if (node instanceof Object) {
		currentElement.id = myindex;
		if (level==0) {
			currentElement.innerHTML = '<img class="delNode" src="'+URL_IMG_DELETE+'" onclick="deleteNode(\''+attrId+'\');" alt="Delete"></img>';
		}
		currentElement.classList.add("config_"+level);
		for(var a in node){
			var rowElement = document.createElement("div");
			rowElement.classList.add("row");
			var labelElement = document.createElement("div");
			labelElement.classList.add("col-25");
			if (a=="class") {
				label = "Type";
			} else if (a=="class") {
				label = "Identifier";
			} else {
				label = a;
			}
			labelElement.innerHTML = "<label for='"+myindex+"-"+a+"'>"
				+label+"</label>";
			rowElement.appendChild(labelElement);
			var attrElement = getElement(myindex, a, node[a], level+1);
			rowElement.appendChild(attrElement);
			currentElement.appendChild(rowElement);
		}
	} else {
		custumInputAttr = ""
		if (attr=="class") {
			custumInputAttr = "readonly ";
			attr = "Type";
		} else if (attr=="class") {
			attr = "Identifier";
		}
		currentElement.innerHTML = "<input type='text' id='"+myindex+"'"
			+custumInputAttr+"value='"+node+"'/>";
	}
	return currentElement;
}
const noSelectObjects = [
	"newnode-contract-peakprice",
	"newnode-contract-offpeakprice"
];
function newNodeAddObject(elementId, element, object) {
	console.log("newNodeAddObject(",elementId, element, object,")");
	for (caract in object) {
		defaultValue = object[caract]
		console.log("newNodeSelectChange() : ",caract," : ",defaultValue)
		var elem = document.createElement("div");
		elem.classList.add("row");
		elem.classList.add(caract);
		
		var sElementId = elementId+"-"+caract;
		if (defaultValue instanceof Array) {
			defaultValue = JSON.stringify(defaultValue);
		}
		if (defaultValue instanceof Object) {
			elem.innerHTML = '<div class="col-25">'
				+'<label for="'+sElementId+'">'+caract+'</label>'
				+'</div><div class="col-75" id="'+sElementId+'"></div>';
			element.appendChild(elem);
			elem2 = document.getElementById(sElementId);
			if (noSelectObjects.includes(sElementId)) {
				newNodeAddObject(sElementId, elem2, defaultValue);
			} else {
				displaySelectElement(sElementId, elem2, defaultValue);
			}
		} else {
			elem.id = sElementId;
			elem.innerHTML = '<div class="col-25">'
				+'<label for="newNode-'+caract+'">'+caract+'</label>'
				+'</div><div class="col-75">'
				+'<input type="text" id="'+sElementId+'-value"'
					+' value="" /></div>';
			element.appendChild(elem);
			 // To avoid encode problems.
			document.getElementById(sElementId+'-value').value = defaultValue;
		}
	}
}
/*
*/
function newNodeSelectChange(selectElementId) {
	var select = document.getElementById(selectElementId+"-select");
	console.log("newNodeSelectChange(",selectElementId,") => ", select.value);
	objectList = objectLists[selectElementId];
	// Warning : Should be better to remove sub-select from selectList but difficult 
	//   We choice to let that memory-leak
	nodeConfig = objectList[select.value];
	if(selectElementId=="newnode") {
		nodeConfig["id"] = "id"+Object.keys(network).length
	}
	addNodeSelecForm = document.getElementById(selectElementId+"-form");
	addNodeSelecForm.innerHTML = "";
	newNodeAddObject(selectElementId, addNodeSelecForm, nodeConfig);
}
function displaySelectElement(elementId, selectDiv, objectList) {
	var selectElement = document.createElement("select");
	selectElement.id = elementId+"-select";
	objectLists[elementId] = objectList;
	selectElement.onchange = function() {
		newNodeSelectChange(elementId);
	};
	var optionElement = document.createElement("option");
	optionElement.value = "";
	optionElement.innerHTML = " - Please select - ";
	selectElement.appendChild(optionElement);
	for (attr in objectList) {
		var optionElement = document.createElement("option");
		optionElement.innerHTML = attr;
		selectElement.appendChild(optionElement);
	}
	selectDiv.appendChild(selectElement);
	var form = document.createElement("div");
	form.id = elementId+'-form';
	selectDiv.appendChild(form);
}
function populateNode(id, node, model, keyvalues) {
	// console.log("populateNode(",id,", ",node,", ",model,", ",keyvalues,")");
	model["id"] = "X";
	for (caract in model) {
		var caractId = caract;
		var modelValue = model[caractId];
		if (modelValue instanceof Object && !(modelValue instanceof Array) ) {
			var key = id+"-"+caractId;
			var key2 = key+"-select";
			if (key2 in keyvalues) {
				var val = keyvalues[key2];
				snode = {"class":val};
				modelValue = modelValue[val];
			} else {
				snode = {};
			}
			var value = populateNode(key, snode, modelValue, keyvalues);
			// console.log(id," for node[",caractId,"] = ", value);
			node[caractId] = value;
		} else {
			var key = id+"-"+caractId+"-value";
			var value = keyvalues[key];
			if (value !== undefined) {
				node[caractId] = value;
			}
		}
	}
	console.log("populateNode(",id,") => ", node);
	return node;
}
function addNode(submitBtn) {
	var keyvalues = {};
	var addNodePopup = document.getElementById("addNodePopup");
	var inputs = addNodePopup.querySelectorAll('input');
	for (i in inputs) {
		input = inputs[i]
		keyvalues[input.id] = input.value;
	}
	selects = addNodePopup.querySelectorAll('select');
	for (i in selects) {
		select = selects[i]
		keyvalues[select.id] = select.value;
	}
	console.log("addNode() : ",keyvalues);
	var id = "newnode"
	var value = keyvalues[id+"-select"];
	var node = {"class":value};
	var model = availableNodes[value];
	node = populateNode(id, node, model, keyvalues);
	network.push(node);
	displayNode(node);
	hideAddNodePopup();
}
var initAddNodePopup = false
function displayAddNodePopup() {
	console.log("displayAddNodePopup()")
	if (!initAddNodePopup) {
		var selectDiv = document.getElementById("newnode-class");
		console.log("displayAddNodePopup() : initAddNodePopup", selectDiv);
		displaySelectElement("newnode", selectDiv, availableNodes);
		initAddNodePopup = true;
	}
	var popup = document.getElementById("addNodePopup");
	popup.classList.add("show");
	popup.style.visibility = "visible";
}
function hideAddNodePopup() {
	// console.log("hideAddNodePopup()")
	var popup = document.getElementById("addNodePopup");
	popup.classList.remove("show");
	popup.style.visibility = "hidden";
}
var defaultId = 0;
function displayNode(node) {
	if (node.id===undefined) {
		node.id = "id"+defaultId;
		defaultId+=1;
	}
	currentElement = getElement("node", node.id, node);
	document.getElementById("nodes").appendChild(currentElement);
}
function displayNetwork() {
	for (n in network) {
		node = network[n];
		console.log("Node:", node);
		displayNode(node);
	}
}
function displayWarningMessages(warningMessages) {
	warningBox = document.getElementById("warningBox");
	if (warningMessages.length>0) {
		warningBox.innerHTML = "There is problems in configurations witch compromise a good behaviour. Please fix those points in configuration, save it and restart OpenHEMS server."
		for (m in warningMessages) {
			msg = warningMessages[m];
			elem = document.createElement("div");
			elem.innerHTML = "• "+msg;
			warningBox.appendChild(elem);
		}
		warningBox.style.display = "block";
	} else {
		warningBox.style.display = "none";
	}
}
