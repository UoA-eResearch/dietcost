$(document).ready(function() {
  $.get('get_nutrient_targets', function(data) {
    console.log(data);
    for (person in data) {
      $('#person').append("<option>" + person + "</option>")
      var fields = data[person];
      console.log(fields);
    }
    $('#person').material_select();
  });
  function get_meal_plan(variables) {
    $.ajax({
      url: 'get_meal_plan',
      type: "POST",
      data: JSON.stringify(variables),
      dataType: "json",
      contentType: "application/json",
      success: function(data) {
        console.log(data);
        $('#meal_plan #items, #nutrients, #diff').empty();
        var keys = Object.keys(data.meal)
        for (var k of keys.sort()) {
          var v = k + ': ' + data.meal[k]; 
          $('#meal_plan #items').append("<li class='collection-item'>" + v + "g</li>");
        }
        var keys = Object.keys(data.nutrients);
        for (var k of keys.sort()) {
          var v = k + ': ' + Math.round(data.nutrients[k] * 100) / 100;
          $('#meal_plan #nutrients').append("<li class='collection-item'>" + v + "</li>");
        }
        var keys = Object.keys(data.diff);
        for (var k of keys.sort()) {
          var v = k + ': ' + Math.round(data.diff[k] * 100) / 100;
          $('#meal_plan #diff').append("<li class='collection-item'>" + v + "</li>");
        }
      }
    });
  }
  get_meal_plan({});
  $('#nutritional_constraints').submit(function( e ) {
    e.preventDefault();
    var variables = {}
    $(this).serializeArray().map(function(x){variables[x.name] = x.value;});
    console.log(variables);
    get_meal_plan(variables);
  });
});