layui.use(['element', 'layer', 'jquery'], function(){
    var element = layui.element;
    var layer = layui.layer;
    var $ = layui.jquery;
    
    $('#fold-menu').on('click', function(){
        var side = $('.layui-side');
        var body = $('.layui-body');
        var footer = $('.layui-footer');
        
        side.toggleClass('layui-hide');
        
        if(side.hasClass('layui-hide')){
            body.css('left', '0');
            footer.css('left', '0');
        } else {
            body.css('left', '200px');
            footer.css('left', '200px');
        }
        
        element.init();
    });
    
    function updateTime(){
        var now = new Date();
        var timeStr = now.getFullYear() + '-' + 
                     (now.getMonth() + 1).toString().padStart(2, '0') + '-' + 
                     now.getDate().toString().padStart(2, '0') + ' ' + 
                     now.getHours().toString().padStart(2, '0') + ':' + 
                     now.getMinutes().toString().padStart(2, '0') + ':' + 
                     now.getSeconds().toString().padStart(2, '0');
        $('#current-time').text(timeStr);
    }
    updateTime();
    setInterval(updateTime, 1000);
    
    element.on('nav(admin-menu)', function(elem){
        var url = elem.attr('lay-url');
        if(url && url !== 'javascript:;'){
            var title = elem.text().trim();
            var id = url.replace(/[\/\?]/g, '_');
            
            if(url === '/admin/'){
                id = 'console';
                title = '控制台';
            }
            
            if($('.layui-tab-title li[lay-id="' + id + '"]').length === 0){
                element.tabAdd('admin-tab', {
                    title: title,
                    content: '<iframe src="' + url + '" frameborder="0" class="admin-iframe"></iframe>',
                    id: id
                });
            }
            element.tabChange('admin-tab', id);
        }
    });
});
