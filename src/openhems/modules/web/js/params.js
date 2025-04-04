DEBUG = false;
var objectLists = {};
/**
 * Function to initiate page to the state of the VPN.
 * @param {bool} connect : True if VPN is connected.
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
				if(DEBUG) console.log('response :  '+retVal);
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
/**
 * On change something in the form, change icon to set to save.
 */
function changeSthg() {
	// if(DEBUG)  console.log("changeSthg()");
		document.getElementById("submitYamlParams")
			.src = "http://localhost:8000/img/save_32.ico";
}
/**
 * 
 */
function getNetwork() {
}
/**
 * Report IHM inputs change to network model in order to send it back.
 */
function setNetwork() {
	nodes = setNodes(nodes, "network.nodes", "node");
	strategys = setNodes(strategys, "server.strategies", "strategy");
	return true;
}
/**
 * Report IHM inputs change to network model in order to send it back.
 */
function setNodes(mynodes, key, nodeType) {
	// if(DEBUG)  console.log("setNodes()");
	var nodes = document.getElementById(nodeType+"s").children;
	var networkById = {};
	// As id can be changed, search orginals ids
	for (n in mynodes) {
		node = mynodes[n]
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
					if (refs[ids.length-1]!=input.value && JSON.stringify(refs[ids.length-1])!=input.value) {
						if(DEBUG)  console.log("setNodes() : ",input.id," has changed from ",refs[ids.length-1] , " to ", input.value);
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
	document.getElementById(key).value = JSON.stringify(myNetwork);
	if(DEBUG)  console.log("setNodes(",nodeType,") => ", myNetwork);
	return mynodes;
}
/**
 * Allow to delete a HTML network node
 *  (It will delete model when HTML is converted to model)
 * @param {*} index : HTML index of the node
 */
function deleteNode(index) {
	var node = document.getElementById("node-"+index);
	node.parentElement.removeChild(node);
	nodes = nodes.filter((node) => node.id!=index);
	strategys = strategys.filter((node) => node.id!=index);
}
/**
 * Get HTML diplay element for a network node model.
 * @param {*} index : The HTML id of the node
 * @param {*} attr : The "name" of the node model.
 * @param {*} node : The node model
 * @param {*} level : The node level.
 * @returns 
 */
function getElement(index, attr, node, level=0) {
	// if(DEBUG)  console.log("getElement(",index,", ",attr,", ",node,", ",level,")")
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
		var input = document.createElement("input");
		input.type = "text";
		input.id = myindex;
		input.value = node;
		currentElement.appendChild(input);
	}
	return currentElement;
}
const objectSelectKeys = [
	"newnode-publicpowergrid-contract"
];
/**
 * Display an object model in a newNode popup.
 * This function is quite similar to ConfigurationManager.completeWithDefaults()
 *  objectSelectKeys is equivalent to selectKeys in ConfigurationManager.completeWithDefaults() (The opposite)
 * @param {*} elementId 
 * @param {*} element 
 * @param {*} object 
 */
function newNodeAddObject(elementId, element, object, key) {
	if(DEBUG)  console.log("newNodeAddObject(",elementId, element, object,")");
	for (caract in object) {
		defaultValue = object[caract]
		if(DEBUG)  console.log("newNodeAddObject() : ",caract," : ",defaultValue)
		var elem = document.createElement("div");
		elem.classList.add("row");
		elem.classList.add(caract);
		
		var sElementId = elementId+"-"+caract;
		var sKey = key+"-"+caract;
		if (defaultValue instanceof Array) {
			defaultValue = JSON.stringify(defaultValue);
		}
		if (defaultValue instanceof Object) {
			elem.innerHTML = '<div class="col-25">'
				+'<label for="'+sElementId+'">'+caract+'</label>'
				+'</div><div class="col-75" id="'+sElementId+'"></div>';
			element.appendChild(elem);
			elem2 = document.getElementById(sElementId);
			if(DEBUG)  console.log("newNodeAddObject() : sElementId=",sElementId)
			if (objectSelectKeys.includes(sKey)) {
				displaySelectElement(sElementId, elem2, defaultValue);
			} else {
				newNodeAddObject(sElementId, elem2, defaultValue, sKey);
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
/**
 * In a newNode popup, when a select change, populate corresponding sub-object.
 * @param {*} selectElementId 
 */
function newNodeSelectChange(selectElementId) {
	var select = document.getElementById(selectElementId+"-select");
	var classname = select.value;
	if(DEBUG)  console.log("newNodeSelectChange(",selectElementId,") => ", classname);
	objectList = objectLists[selectElementId];
	// Warning : Should be better to remove sub-select from selectList but difficult 
	//   We choice to let that memory-leak
	nodeConfig = objectList[classname];
	if(selectElementId=="newnode") {
		nodeConfig["id"] = "id"+Object.keys(nodes).length+Object.keys(strategys).length
	}
	addNodeSelecForm = document.getElementById(selectElementId+"-form");
	addNodeSelecForm.innerHTML = "";
	newNodeAddObject(selectElementId, addNodeSelecForm, nodeConfig, selectElementId+"-"+classname);
}
/**
 * Diplay a HTML select element based on Object model of the list.
 * @param {*} elementId : Base HTML id
 * @param {*} selectDiv : The select div
 * @param {*} objectList : Object model of the list
 */
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
/**
 * Convert dict key/values to object:
 * {
 *  a-b-c:1
 *  a-b-f:4
 *  a-d:2
 *  a-e:3
 * } => a:{b:{c:1, f:4}, d:2, e:3}
 *
 * @param {*} id 
 * @param {*} node 
 * @param {*} model 
 * @param {*} keyvalues 
 * @returns 
 */
function populateNode(id, node, model, keyvalues) {
	// if(DEBUG)  console.log("populateNode(",id,", ",node,", ",model,", ",keyvalues,")");
	model["id"] = "X";
	for (caract in model) {
		var caractId = caract;
		var modelValue = model[caractId];
		if (modelValue instanceof Object && !(modelValue instanceof Array) ) {
			var key = id+"-"+caractId;
			var key2 = key+"-select";
			if (key2 in keyvalues) {
				var classname = keyvalues[key2];
				snode = {"class":classname};
				modelValue = modelValue[classname];
			} else {
				snode = {};
			}
			var value = populateNode(key, snode, modelValue, keyvalues);
			// if(DEBUG)  console.log(id," for node[",caractId,"] = ", value);
			node[caractId] = value;
		} else {
			var key = id+"-"+caractId+"-value";
			var value = keyvalues[key];
			if (value !== undefined) {
				node[caractId] = value;
			}
		}
	}
	if(DEBUG)  console.log("populateNode(",id,") => ", node);
	return node;
}
/**
 * On click to add node from the popup,
 *  add the node in the HTML and close the popup.
 * @param {*} submitBtn 
 */
function addNode(addBtn) {
	nodeType = addBtn.dataset.nodeType;
	if(DEBUG)  console.log("addNode(",nodeType,")");
	// Search key/values in the popup form
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
	if(DEBUG)  console.log("addNode() : ",keyvalues);
	// Convert keyvalues to object
	var newnodeId = "newnode"
	var classname = keyvalues[newnodeId+"-select"];
	var newnode = {"class":classname};
	if(DEBUG)  console.log("addNode() : ",classname, " = ", newnode);
	var model = availableNodes[nodeType][classname];
	node = populateNode(newnodeId, newnode, model, keyvalues);
	if (nodeType=="node") {
		nodes.push(newnode);
	} else {
		strategys.push(newnode);
	}
	// display the object
	displayNode(newnode, nodeType);
	hideAddNodePopup();
}
var initAddNodePopup = "";
/**
 * When want to add a new node (Click on + button next to the list),
 * diplay an appropriate popup.
 */
function displayAddNodePopup(nodeType="node") {
	if(DEBUG)  console.log("displayAddNodePopup(",nodeType,")");
	if (initAddNodePopup!=nodeType) {
		var selectDiv = document.getElementById("newnode-class");
		if(DEBUG)  console.log("displayAddNodePopup() : initAddNodePopup", selectDiv);
		selectDiv.innerHTML = "";
		myAvailableNodes = availableNodes[nodeType]
		displaySelectElement("newnode", selectDiv, myAvailableNodes);
		addBtn = document.getElementById("addNodeBtn");
		addBtn.dataset.nodeType = nodeType;
		initAddNodePopup = nodeType;
	}
	var popup = document.getElementById("addNodePopup");
	popup.classList.add("show");
	popup.style.visibility = "visible";
}
/**
 * Hide the "new node popup".
 */
function hideAddNodePopup() {
	// if(DEBUG)  console.log("hideAddNodePopup()")
	var popup = document.getElementById("addNodePopup");
	popup.classList.remove("show");
	popup.style.visibility = "hidden";
}
var defaultId = 0;
/**
 * Append a node model to the display list.
 * @param {object} node
 */
function displayNode(node, nodeType="node") {
	if(DEBUG)  console.log("displayNode(",nodeType,",",node,")");
	if (node.id===undefined) {
		node.id = "id"+defaultId;
		defaultId+=1;
	}
	currentElement = getElement("node", node.id, node);
	document.getElementById(nodeType+"s").appendChild(currentElement);
}
/**
 * Display the network model.
 */
networkDisplayed = false;
function displayNetwork() {
	if (networkDisplayed) {
		console.log("Warning : Network already displayed.");
		// return;
	}
	nodeType="node";
	document.getElementById(nodeType+"s").innerHTML = "";
	for (n in nodes) {
		node = nodes[n];
		displayNode(node, nodeType);
	}
	nodeType="strategy";
	document.getElementById(nodeType+"s").innerHTML = "";
	for (n in strategys) {
		node = strategys[n];
		displayNode(node, nodeType);
	}
	networkDisplayed = true;
}
/**
 * Display global warning message witch indicate a error loading the YAML file (At OpenHEMS startup).
 * @param {*} warningMessages 
 */
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
