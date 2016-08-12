$(document).ready(function() {
  function round(float) {
    return Math.round(float * 100) / 100;
  }
  $.get('get_nutrient_targets', function(data) {
    console.log(data);
    for (person in data) {
      var selected = '';
      var fields = data[person];
      if (person == 'adult man') {
        selected = 'selected';
        $.each(fields, function(name, defaults) {
          var machine_name = name.replace(/[ %*]+/g, '_');
          $("#dynamic_fields").append('<div id="' + machine_name + '" class="row"><p class="nt_label">' + name + '</p><div class="input-field col s2"><input value="' + round(defaults.min) + '" type="text" class="min validate"><label for="min">Min</label></div><div class="slider-wrapper col s8"><div class="slider"></div></div><div class="input-field col s2"><input type="text" value="' + round(defaults.max) + '" class="max validate"><label for="max">Max</label></div></div>');
          var slider = $('#' + machine_name + ' div.slider')[0];
          var range = {'min': 0, 'max': defaults.max * 2}
          if (name == 'Energy kJ') {
            range = {'min': defaults.min * .9, 'max': defaults.max * 1.1}
          }
          noUiSlider.create(slider, {
            start: [defaults.min, defaults.max],
            connect: true,
            step: 1,
            behaviour: 'tap-drag',
            pips: {
              mode: 'count',
              values: 6,
              density: 4
            },
            range: range,
            format: {
              to: function(value) {
                return parseInt(value);
              },
              from: function(value) {
                return parseInt(value);
              }
            }
          });
          slider.noUiSlider.on('slide', function(values, handle) {
            // min handle = 0, max handle = 1
            if (handle) {
              $('#' + machine_name + ' input.max').val(values[handle]);
            } else {
              $('#' + machine_name + ' input.min').val(values[handle]);
            }
          });
          $('#' + machine_name + ' input.min').keyup(function() {
            slider.noUiSlider.set([$(this).val(), null]);
          });
          $('#' + machine_name + ' input.max').keyup(function() {
            slider.noUiSlider.set([null, $(this).val()]);
          });
        });
      }
      $('#person').append("<option " + selected + ">" + person + "</option>")
    }
    $('#person').material_select();
    Materialize.updateTextFields();
    $('#person').change(function (e) {
      console.log($(this).val());
    });
  });
  function get_meal_plans(variables) {
    $('#progress').show();
    $.ajax({
      url: 'get_meal_plans',
      type: "POST",
      data: JSON.stringify(variables),
      dataType: "json",
      contentType: "application/json",
      success: function(data) {
        $('#progress').hide();
        console.log(data);
        $('#meal_plans').empty();
        var totalPrice = 0;
        var totalVariety = 0;
        for (var hash in data) {
          var o = data[hash];
          var items = "";
          var keys = Object.keys(o.meal).sort();
          for (var i in keys) {
            var k = keys[i];
            var amount = o.meal[k];
            items += "<tr><td>" + k + "</td><td>" + round(amount) + "g</td></tr>";
          }
          var table = "<table class='highlight bordered'><thead><tr><th data-field='name'>Name</th><th data-field='amount'>Amount</th></tr></thead><tbody>" + items + "</tbody></table>";
          var collapsibleTable = "<ul class='collapsible' data-collapsible='accordion'><li><div class='collapsible-header'><i class='material-icons'>receipt</i>Items</div><div class='collapsible-body'>" + table + "</div></li></ul>";
          var card = "<div class='col s12 m6'><div class='card hoverable'><div class='card-content'>" + table + "</div><div class='card-action'><p class='price'>Price: $" + round(o.price) + "</p><p class='variety'>Variety: " + round(o.variety) + "</p></div></div></div>";
          $('#meal_plans').append(card);
          totalPrice += o.price;
          totalVariety += o.variety;
        }
        $('.collapsible').collapsible();
        var l = Object.keys(data).length;
        $('#summary').html("Total meal plans: " + l + ". Average price: $" + round(totalPrice / l) + ". Average variety: " + round(totalVariety / l));
      }
    });
  }
  get_meal_plans({person: 'adult man'});
  $('#nutritional_constraints').submit(function( e ) {
    e.preventDefault();
    var variables = {}
    $(this).serializeArray().map(function(x){variables[x.name] = x.value;});
    console.log(variables);
    get_meal_plans(variables);
  });
});