// include node fs module
var fs = require('fs');
var data ='Learn Node FS module';
  
// writeFile function with filename, content and callback function
fs.writeFile('newfile.txt', data, function (err) {
	if (err) throw err;
	console.log('File is created successfully.');
});
