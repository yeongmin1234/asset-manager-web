export const FILE_RULES={
 excel:{extensions:["xls","xlsx"],mimeTypes:["application/vnd.ms-excel","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],maxBytes:20*1024*1024,maxFiles:1,maxRows:50000},
 text:{extensions:["txt"],mimeTypes:["text/plain"],maxBytes:10*1024*1024,maxFiles:1,maxRows:100000},
 image:{extensions:["jpg","jpeg","png"],mimeTypes:["image/jpeg","image/png"],maxBytes:5*1024*1024,maxFiles:1,maxRows:1},
};
