$(document).ready(function() {
  $.get('get_nutrient_targets', function(data) {
    console.log(data);
    for (person in data) {
      $('#person').append("<option>" + person + "</option>")
      var fields = data[person];
    }
    $('#person').material_select();
  });
  function round(float) {
    return Math.round(float * 100) / 100;
  }
  function get_meal_plans(variables) {
    $.ajax({
      url: 'get_meal_plans',
      type: "POST",
      data: JSON.stringify(variables),
      dataType: "json",
      contentType: "application/json",
      success: function(data) {
        console.log(data);
        $('#meal_plans').empty();
        for (var hash in data) {
          var o = data[hash];
          var items = "";
          var keys = Object.keys(o.meal).sort();
          for (var i in keys) {
            var k = keys[i];
            var amount = o.meal[k];
            items += "<li class='collection-item'>" + k + ": " + round(amount) + "g</li>";
          }
          $('#meal_plans').append("<div class='col s12 m6'><div class='card'><div class='card-content'><p><ul class='collection'>" + items + "</ul></p></div><div class='card-action'><p class='price'>Price: $" + round(o.price) + "</p><p class='variety'>Variety: " + round(o.variety) + "</p></div></div></div>");
        }
      }
    });
  }
  get_meal_plans({});
  $('#nutritional_constraints').submit(function( e ) {
    e.preventDefault();
    var variables = {}
    $(this).serializeArray().map(function(x){variables[x.name] = x.value;});
    console.log(variables);
    get_meal_plans(variables);
  });
});